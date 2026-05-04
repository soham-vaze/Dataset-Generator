import json
import logging
import math
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

import pandas as pd

from generators.utils import call_model, save_dataset

logger = logging.getLogger(__name__)


# ======================================================
# 1️⃣ LOAD AND PARSE USER SCHEMA
# ======================================================

def load_schema(schema_path: str) -> Dict[str, List[Dict[str, str]]]:
    with open(schema_path, "r", encoding="utf-8-sig") as f:
        schema = json.load(f)

    # Handle top-level list
    if isinstance(schema, list):
        schema = {"tables": schema}

    if "tables" not in schema:
        raise ValueError("Schema must contain 'tables' key")

    tables = schema["tables"]

    # 🔥 Convert dict → list
    if isinstance(tables, dict):
        logger.warning("Schema 'tables' is a dict — converting to list format")

        new_tables = []
        for table_name, table_data in tables.items():

            # If list → columns
            if isinstance(table_data, list):
                new_tables.append({
                    "table_name": table_name,
                    "columns": table_data
                })

            # If dict → already structured
            elif isinstance(table_data, dict):
                new_tables.append({
                    "table_name": table_name,
                    **table_data
                })

            else:
                raise ValueError(f"Invalid format for table '{table_name}'")

        tables = new_tables
        schema["tables"] = tables

    # 🔥 Normalize columns
    for table in tables:

        if "table_name" not in table or "columns" not in table:
            raise ValueError("Each table must have 'table_name' and 'columns'")

        fixed_columns = []

        for col in table["columns"]:

            # Already correct
            if isinstance(col, dict):
                if "name" not in col or "type" not in col:
                    raise ValueError(f"Invalid column format in {table['table_name']}")
                fixed_columns.append(col)

            # 🔥 Convert string → dict
            elif isinstance(col, str):
                fixed_columns.append({
                    "name": col,
                    "type": "INTEGER" if col.endswith("id") else "TEXT"
                })

            else:
                raise ValueError(f"Invalid column type in {table['table_name']}")

        table["columns"] = fixed_columns

    return schema


def json_to_sqlite_ddl(schema: Dict[str, List[Dict[str, str]]]):

    ddl_statements = []
    column_map = {}

    for table in schema["tables"]:

        table_name = table["table_name"]
        column_defs = []
        column_map[table_name] = []

        for col in table["columns"]:

            # 🔥 SAFETY (extra protection)
            if isinstance(col, str):
                col = {"name": col, "type": "TEXT"}

            if not isinstance(col, dict):
                raise ValueError(f"Invalid column in table '{table_name}'")

            col_name = col["name"]
            col_type = col["type"]

            col_def = f"{col_name} {col_type}"

            if col.get("primary_key"):
                col_def += " PRIMARY KEY"

            column_defs.append(col_def)
            column_map[table_name].append(col_name)

        ddl = f"CREATE TABLE {table_name} ({', '.join(column_defs)});"
        ddl_statements.append(ddl)

    return ddl_statements, column_map


# ======================================================
# 2️⃣ GENERATE SQL QUERY
# ======================================================

def generate_sql(schema_ddl: List[str],
                 model: str,
                 temperature: float = 0.7) -> str:

    schema_text = "\n".join(schema_ddl)

    prompt = f"""
You are an expert SQL query generator.

Given the following database schema, generate ONE valid SQL query.

Only output the SQL query.

Schema:
{schema_text}
"""

    response = call_model(prompt, model, temperature=temperature)

    sql_query = response.strip()

    sql_query = re.sub(r"```sql|```", "", sql_query).strip()

    return sql_query


# ======================================================
# 3️⃣ COLUMN VALIDATION
# ======================================================

def validate_columns(sql_query: str,
                     column_map: Dict[str, List[str]]) -> bool:

    SQL_KEYWORDS = {
        "SELECT", "FROM", "WHERE", "AND", "OR",
        "JOIN", "ON", "GROUP", "BY", "ORDER",
        "HAVING", "COUNT", "SUM", "AVG", "MIN", "MAX",
        "LIMIT", "AS", "INNER", "LEFT", "RIGHT",
        "INSERT", "UPDATE", "DELETE", "INTO", "VALUES", "SET",
        "NOT", "NULL", "IN", "BETWEEN", "LIKE", "IS", "EXISTS",
        "DISTINCT", "DESC", "ASC", "UNION", "ALL", "CREATE", "TABLE",
        "CROSS", "OUTER", "FULL", "CASE", "WHEN", "THEN", "ELSE", "END",
        "TRUE", "FALSE", "OFFSET", "FETCH", "FIRST", "NEXT", "ROWS",
        "ONLY", "NATURAL", "USING", "EXCEPT", "INTERSECT", "TOP",
        "WITH", "RECURSIVE", "OVER", "PARTITION", "RANK", "ROW_NUMBER",
    }

    tokens = re.findall(r"\b[a-zA-Z_]+\b", sql_query)

    valid_columns = {col for cols in column_map.values() for col in cols}

    valid_tables = set(column_map.keys())

    for token in tokens:

        if token.upper() in SQL_KEYWORDS:
            continue

        if token in valid_tables:
            continue

        if token in valid_columns:
            continue

        # Unknown identifier — likely a hallucinated column/table
        logger.debug("Unknown token in SQL: %s", token)
        return False

    return True


# ======================================================
# 4️⃣ EXECUTION VALIDATION
# ======================================================

def validate_execution(sql_query: str,
                       ddl_statements: List[str]) -> bool:

    try:
        with sqlite3.connect(":memory:") as conn:
            cursor = conn.cursor()
            for ddl in ddl_statements:
                cursor.execute(ddl)
            cursor.execute(sql_query)
        return True

    except sqlite3.Error as e:
        logger.debug("SQL execution validation failed: %s", e)
        return False


# ======================================================
# 5️⃣ GENERATE ENGLISH QUESTION FROM SQL
# ======================================================

def generate_question_from_sql(sql_query: str,
                               model: str,
                               temperature: float = 0.6) -> str:

    prompt = f"""
Convert the following SQL query into a clear natural language English question.

Only output the question.

SQL:
{sql_query}
"""

    response = call_model(prompt, model, temperature=temperature)

    question = response.strip()

    question = re.sub(r"```", "", question).strip()

    return question


# ======================================================
# 6️⃣ SAVE DATASET — Uses shared save_dataset from generators.utils
# ======================================================


# ======================================================
# 7️⃣ MAIN ENGINE
# ======================================================

def generate_nl2sql_dataset(schema_path: str,
                            output_path: str,
                            model: str,
                            num_samples: int = 10) -> None:

    logger.info("Generating NL-SQL dataset")

    schema = load_schema(schema_path)

    ddl_statements, column_map = json_to_sqlite_ddl(schema)

    dataset_rows: List[Dict[str, str]] = []

    existing_sql: Set[str] = set()
    existing_questions: Set[str] = set()

    if os.path.exists(output_path):

        existing_df = pd.read_csv(output_path)

        if "sql_query" in existing_df.columns:
            existing_sql = set(existing_df["sql_query"].astype(str))

        if "english_question" in existing_df.columns:
            existing_questions = set(existing_df["english_question"].astype(str))

    batch_size = min(10, num_samples)

    total_batches = math.ceil(num_samples / batch_size)

    logger.info("Using batch size %d (%d batches)", batch_size, total_batches)

    attempts = 0

    max_attempts = num_samples * 5


    while len(dataset_rows) < num_samples and attempts < max_attempts:

        attempts += 1

        sql_query = generate_sql(ddl_statements, model)

        normalized_sql = " ".join(sql_query.lower().split())

        if normalized_sql in existing_sql:
            logger.debug("Duplicate SQL detected")
            continue

        if not validate_columns(sql_query, column_map):
            logger.debug("Column validation failed")
            continue

        if not validate_execution(sql_query, ddl_statements):
            logger.debug("SQL execution failed")
            continue

        question = generate_question_from_sql(sql_query, model)

        normalized_question = " ".join(question.lower().split())

        if normalized_question in existing_questions:
            logger.debug("Duplicate question detected")
            continue

        dataset_rows.append({
            "english_question": question,
            "sql_query": sql_query,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        existing_sql.add(normalized_sql)
        existing_questions.add(normalized_question)

        logger.info("Valid pair generated (%d/%d)", len(dataset_rows), num_samples)


    if dataset_rows:

        save_dataset(dataset_rows, output_path)

        logger.info("Saved %d unique pairs.", len(dataset_rows))
        

    else:

        logger.warning("No valid unique pairs generated.")


# ======================================================
# EXAMPLE
# ======================================================

if __name__ == "__main__":

    generate_nl2sql_dataset(
        schema_path="/home/soham/dataset_generator/schemas/schema1.json",
        output_path="/home/soham/dataset_generator/datasets/nl2sql_dataset_v1.csv",
        model="gemma3:1b",
        num_samples=20
    )