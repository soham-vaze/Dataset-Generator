import json
import logging
import math
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Set

import pandas as pd

from generators.utils import call_model, save_dataset

logger = logging.getLogger(__name__)

# ======================================================
# STARTUP SQLGLOT CHECK
# ======================================================

try:
    import sqlglot
    from sqlglot import exp

    SQLGLOT_AVAILABLE = True

    logger.info(
        "sqlglot loaded successfully | version=%s | path=%s",
        sqlglot.__version__,
        sqlglot.__file__,
    )

except Exception as e:

    SQLGLOT_AVAILABLE = False

    logger.exception(
        "sqlglot initialization failed: %s",
        e,
    )


# ======================================================
# 1️⃣ LOAD AND PARSE USER SCHEMA
# ======================================================

def load_schema(schema_path: str) -> Dict[str, List[Dict[str, str]]]:

    with open(schema_path, "r", encoding="utf-8-sig") as f:
        schema = json.load(f)

    if isinstance(schema, list):
        schema = {"tables": schema}

    if "tables" not in schema:
        raise ValueError("Schema must contain 'tables' key")

    tables = schema["tables"]

    # Convert dict → list
    if isinstance(tables, dict):

        logger.warning(
            "Schema 'tables' is a dict — converting to list format"
        )

        new_tables = []

        for table_name, table_data in tables.items():

            if isinstance(table_data, list):

                new_tables.append({
                    "table_name": table_name,
                    "columns": table_data,
                })

            elif isinstance(table_data, dict):

                new_tables.append({
                    "table_name": table_name,
                    **table_data,
                })

            else:
                raise ValueError(
                    f"Invalid format for table '{table_name}'"
                )

        tables = new_tables

        schema["tables"] = tables

    # Normalize columns
    for table in tables:

        if "table_name" not in table or "columns" not in table:
            raise ValueError(
                "Each table must have 'table_name' and 'columns'"
            )

        fixed_columns = []

        for col in table["columns"]:

            if isinstance(col, dict):

                if "name" not in col or "type" not in col:

                    raise ValueError(
                        f"Invalid column format in {table['table_name']}"
                    )

                fixed_columns.append(col)

            elif isinstance(col, str):

                fixed_columns.append({
                    "name": col,
                    "type": (
                        "INTEGER"
                        if col.lower().endswith("id")
                        else "TEXT"
                    ),
                })

            else:
                raise ValueError(
                    f"Invalid column type in {table['table_name']}"
                )

        table["columns"] = fixed_columns

    return schema


# ======================================================
# 2️⃣ JSON → SQLITE DDL
# ======================================================

def json_to_sqlite_ddl(schema):

    ddl_statements = []

    column_map = {}

    for table in schema["tables"]:

        table_name = table["table_name"]

        column_defs = []

        column_map[table_name] = []

        for col in table["columns"]:

            if isinstance(col, str):
                col = {
                    "name": col,
                    "type": "TEXT",
                }

            col_name = col["name"]

            col_type = col["type"]

            col_def = f"{col_name} {col_type}"

            if col.get("primary_key"):
                col_def += " PRIMARY KEY"

            column_defs.append(col_def)

            column_map[table_name].append(col_name)

        ddl = (
            f"CREATE TABLE {table_name} "
            f"({', '.join(column_defs)});"
        )

        ddl_statements.append(ddl)

    return ddl_statements, column_map


# ======================================================
# 3️⃣ CLEAN RAW MODEL OUTPUT
# ======================================================

def extract_sql_query(response: str) -> str:
    """
    Extract clean SQL query from noisy LLM output.
    """

    if not response:
        return ""

    text = response.strip()

    # Remove markdown
    text = re.sub(
        r"```sql",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"```",
        "",
        text,
    )

    # Find first SQL keyword
    sql_match = re.search(
        r"\b(SELECT|WITH|INSERT|UPDATE|DELETE)\b",
        text,
        re.IGNORECASE,
    )

    if not sql_match:
        return ""

    text = text[sql_match.start():]

    # Cut after final semicolon
    if ";" in text:
        text = text[: text.rfind(";") + 1]

    cleaned_lines = []

    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        # Stop explanations
        if re.match(
            r"^(Explanation|This query|Here is|The query|Note:)",
            stripped,
            re.IGNORECASE,
        ):
            break

        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()

    return cleaned


# ======================================================
# 4️⃣ GENERATE SQL QUERY
# ======================================================

def generate_sql(
    schema_ddl: List[str],
    model: str,
    temperature: float = 0.7,
) -> str:

    schema_text = "\n".join(schema_ddl)

    prompt = f"""
You are an expert SQLite SQL generator.

Generate EXACTLY ONE valid SQLite SQL query.

STRICT RULES:
- Output ONLY SQL
- Do NOT explain anything
- Do NOT include markdown
- Do NOT include comments
- Do NOT say "Here is the SQL query"
- Start directly with SELECT or WITH
- End with semicolon
- Use ONLY schema tables and columns
- SQLite syntax only
- Generate realistic and diverse queries

Schema:
{schema_text}
"""

    response = call_model(
        prompt,
        model,
        temperature=temperature,
    )

    sql_query = extract_sql_query(response)

    logger.debug(
        "Raw model response:\n%s\n\nCleaned SQL:\n%s",
        response,
        sql_query,
    )

    return sql_query


# ======================================================
# 5️⃣ AST-BASED COLUMN VALIDATION
# ======================================================

def validate_columns(
    sql_query: str,
    column_map: Dict[str, List[str]],
) -> bool:

    if not sql_query:
        return False

    if not SQLGLOT_AVAILABLE:

        logger.warning(
            "sqlglot unavailable — skipping AST validation"
        )

        return True

    try:

        statements = sqlglot.parse(
            sql_query,
            dialect="sqlite",
        )

    except Exception as exc:

        logger.warning(
            "sqlglot parse error: %s",
            exc,
        )

        return False

    if not statements or statements[0] is None:

        logger.warning(
            "sqlglot returned empty AST"
        )

        return False

    ast = statements[0]

    valid_tables: Set[str] = {
        t.lower()
        for t in column_map
    }

    valid_cols_by_table: Dict[str, Set[str]] = {
        t.lower(): {
            c.lower()
            for c in cols
        }
        for t, cols in column_map.items()
    }

    all_valid_columns: Set[str] = {
        c
        for cols in valid_cols_by_table.values()
        for c in cols
    }

    table_alias_map: Dict[str, str] = {}

    non_schema_refs: Set[str] = set()

    column_aliases: Set[str] = set()

    # --------------------------------------------------
    # TABLE ALIASES
    # --------------------------------------------------

    for tbl in ast.find_all(exp.Table):

        tname = (tbl.name or "").lower()

        alias = (tbl.alias or "").lower()

        if alias:

            if tname in valid_tables:
                table_alias_map[alias] = tname

            else:
                non_schema_refs.add(alias)

    # --------------------------------------------------
    # CTEs
    # --------------------------------------------------

    for cte in ast.find_all(exp.CTE):

        if cte.alias:
            non_schema_refs.add(
                cte.alias.lower()
            )

    # --------------------------------------------------
    # SUBQUERY ALIASES
    # --------------------------------------------------

    for subq in ast.find_all(exp.Subquery):

        if subq.alias:
            non_schema_refs.add(
                subq.alias.lower()
            )

    # --------------------------------------------------
    # COLUMN ALIASES
    # --------------------------------------------------

    for alias_node in ast.find_all(exp.Alias):

        if alias_node.alias:
            column_aliases.add(
                alias_node.alias.lower()
            )

    # --------------------------------------------------
    # VALIDATE TABLES
    # --------------------------------------------------

    referenced_tables: Set[str] = set()

    for tbl in ast.find_all(exp.Table):

        tname = (tbl.name or "").lower()

        if not tname:
            continue

        if tname in non_schema_refs:
            continue

        if tname not in valid_tables:

            logger.debug(
                "Column validation FAILED | unknown table: '%s'",
                tname,
            )

            return False

        referenced_tables.add(tname)

    # --------------------------------------------------
    # VALIDATE COLUMNS
    # --------------------------------------------------

    missing: List[str] = []

    for col in ast.find_all(exp.Column):

        col_name = (col.name or "").lower()

        if not col_name or col_name == "*":
            continue

        table_prefix = (col.table or "").lower()

        if table_prefix:

            if table_prefix in non_schema_refs:
                continue

            real_table = table_alias_map.get(
                table_prefix,
                table_prefix,
            )

            if real_table not in valid_tables:
                continue

            if col_name not in valid_cols_by_table.get(
                real_table,
                set(),
            ):

                missing.append(
                    f"{table_prefix}.{col_name}"
                )

        else:

            if col_name in all_valid_columns:
                continue

            if col_name in column_aliases:
                continue

            missing.append(col_name)

    if missing:

        logger.debug(
            "Column validation FAILED | unresolved columns=%s",
            missing,
        )

        return False

    logger.debug(
        "Column validation PASSED | tables=%s",
        sorted(referenced_tables),
    )

    return True


# ======================================================
# 6️⃣ EXECUTION VALIDATION
# ======================================================

def validate_execution(
    sql_query: str,
    ddl_statements: List[str],
) -> bool:

    try:

        with sqlite3.connect(":memory:") as conn:

            cursor = conn.cursor()

            for ddl in ddl_statements:
                cursor.execute(ddl)

            cursor.execute(sql_query)

        return True

    except sqlite3.Error as e:

        logger.debug(
            "SQL execution validation failed: %s",
            e,
        )

        return False


# ======================================================
# 7️⃣ GENERATE ENGLISH QUESTION
# ======================================================

def generate_question_from_sql(
    sql_query: str,
    model: str,
    temperature: float = 0.6,
) -> str:

    prompt = f"""
Convert the following SQL query into a clear natural language English question.

IMPORTANT:
- Output ONLY the question
- Do NOT explain anything
- Do NOT include markdown

SQL:
{sql_query}
"""

    response = call_model(
        prompt,
        model,
        temperature=temperature,
    )

    question = response.strip()

    question = re.sub(
        r"```",
        "",
        question,
    ).strip()

    return question


# ======================================================
# 8️⃣ MAIN ENGINE
# ======================================================

def generate_nl2sql_dataset(
    schema_path: str,
    output_path: str,
    model: str,
    num_samples: int = 10,
) -> None:

    logger.info(
        "Generating NL-SQL dataset"
    )

    schema = load_schema(schema_path)

    ddl_statements, column_map = json_to_sqlite_ddl(
        schema
    )

    dataset_rows: List[Dict[str, str]] = []

    existing_sql: Set[str] = set()

    existing_questions: Set[str] = set()

    if os.path.exists(output_path):

        existing_df = pd.read_csv(output_path)

        if "sql_query" in existing_df.columns:

            existing_sql = {
                " ".join(
                    x.lower().split()
                )
                for x in existing_df["sql_query"].astype(str)
            }

        if "english_question" in existing_df.columns:

            existing_questions = {
                " ".join(
                    x.lower().split()
                )
                for x in existing_df["english_question"].astype(str)
            }

    batch_size = min(10, num_samples)

    total_batches = math.ceil(
        num_samples / batch_size
    )

    logger.info(
        "Using batch size %d (%d batches)",
        batch_size,
        total_batches,
    )

    attempts = 0

    max_attempts = max(
        num_samples * 10,
        100,
    )

    total_duplicate_sql = 0
    total_duplicate_question = 0
    total_column_failures = 0
    total_execution_failures = 0

    while (
        len(dataset_rows) < num_samples
        and attempts < max_attempts
    ):

        attempts += 1

        temperature = min(
            0.7 + (attempts * 0.01),
            1.2,
        )

        logger.info(
            "Attempt %d/%d (have %d/%d)",
            attempts,
            max_attempts,
            len(dataset_rows),
            num_samples,
        )

        sql_query = generate_sql(
            ddl_statements,
            model,
            temperature=temperature,
        )

        if not sql_query:

            logger.debug(
                "Empty SQL after extraction"
            )

            total_column_failures += 1

            continue

        normalized_sql = " ".join(
            sql_query.lower().split()
        )

        if normalized_sql in existing_sql:

            logger.debug(
                "Duplicate SQL detected"
            )

            total_duplicate_sql += 1

            continue

        if not validate_columns(
            sql_query,
            column_map,
        ):

            logger.debug(
                "Column validation failed"
            )

            total_column_failures += 1

            continue

        if not validate_execution(
            sql_query,
            ddl_statements,
        ):

            logger.debug(
                "Execution validation failed"
            )

            total_execution_failures += 1

            continue

        question = generate_question_from_sql(
            sql_query,
            model,
        )

        normalized_question = " ".join(
            question.lower().split()
        )

        if normalized_question in existing_questions:

            logger.debug(
                "Duplicate question detected"
            )

            total_duplicate_question += 1

            continue

        dataset_rows.append({
            "english_question": question,
            "sql_query": sql_query,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        })

        existing_sql.add(normalized_sql)

        existing_questions.add(
            normalized_question
        )

        logger.info(
            "Valid pair generated (%d/%d)",
            len(dataset_rows),
            num_samples,
        )

    # ==================================================
    # SAVE
    # ==================================================

    if dataset_rows:

        save_dataset(
            dataset_rows,
            output_path,
        )

        logger.info(
            "Saved %d unique pairs.",
            len(dataset_rows),
        )

    else:

        logger.warning(
            "No valid unique pairs generated."
        )

    # ==================================================
    # SUMMARY
    # ==================================================

    logger.info(
        "===== NL-SQL Generation Summary ====="
    )

    logger.info(
        "Requested: %d",
        num_samples,
    )

    logger.info(
        "Valid saved: %d",
        len(dataset_rows),
    )

    logger.info(
        "Duplicate SQL skipped: %d",
        total_duplicate_sql,
    )

    logger.info(
        "Duplicate question skipped: %d",
        total_duplicate_question,
    )

    logger.info(
        "Column validation failures: %d",
        total_column_failures,
    )

    logger.info(
        "Execution validation failures: %d",
        total_execution_failures,
    )

    logger.info(
        "Attempts used: %d/%d",
        attempts,
        max_attempts,
    )

    logger.info(
        "Fulfillment: %.1f%%",
        (
            len(dataset_rows)
            / num_samples
            * 100
        ) if num_samples > 0 else 0,
    )

    logger.info(
        "====================================="
    )


# ======================================================
# EXAMPLE
# ======================================================

if __name__ == "__main__":

    generate_nl2sql_dataset(
        schema_path="schemas/schema1.json",
        output_path="datasets/nl2sql_dataset.csv",
        model="llama3.1:8b",
        num_samples=20,
    )