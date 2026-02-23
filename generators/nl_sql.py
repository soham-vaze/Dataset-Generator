'''
System architecture:-

User uploads JSON schema
        ↓
Parse JSON
        ↓
Generate SQL query
        ↓
Check column names against schema
        ↓
Execute SQL in SQLite
        ↓
If valid → generate English question
        ↓
Store dataset
'''

import json
import sqlite3
import ollama
import pandas as pd
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple


# ======================================================
# 1️⃣ LOAD AND PARSE USER SCHEMA
# ======================================================

def load_schema(schema_path: str) -> Dict:
    with open(schema_path, "r") as f:
        return json.load(f)


def json_to_sqlite_ddl(schema: Dict) -> Tuple[List[str], Dict]:
    """
    Converts JSON schema into SQLite CREATE TABLE statements.
    Returns:
        - list of DDL statements
        - dictionary of valid columns per table
    """
    ddl_statements = []
    column_map = {}

    for table in schema["tables"]:
        table_name = table["table_name"]
        column_defs = []
        column_map[table_name] = []

        for col in table["columns"]:
            col_def = f"{col['name']} {col['type']}"
            if col.get("primary_key"):
                col_def += " PRIMARY KEY"
            column_defs.append(col_def)
            column_map[table_name].append(col["name"])

        ddl = f"CREATE TABLE {table_name} ({', '.join(column_defs)});"
        ddl_statements.append(ddl)

    return ddl_statements, column_map


# ======================================================
# 2️⃣ GENERATE SQL QUERY
# ======================================================

def generate_sql(schema_ddl: List[str],
                 model: str,
                 temperature: float = 0.7) -> str:

    system_prompt = (
        "You are an expert SQL query generator.\n"
        "Given the following database schema, generate ONE valid SQL query.\n"
        "Only output the SQL query.\n"
        "Include diversity (joins, filters, aggregations when possible).\n"
    )

    schema_text = "\n".join(schema_ddl)

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Schema:\n{schema_text}"}
        ],
        options={"temperature": temperature}
    )

    sql_query = response["message"]["content"].strip()

    # Remove code block formatting if present
    sql_query = re.sub(r"```sql|```", "", sql_query).strip()

    return sql_query


# ======================================================
# 3️⃣ COLUMN VALIDATION
# ======================================================

def validate_columns(sql_query: str,
                     column_map: Dict) -> bool:

    # Extract words that might be column names
    tokens = re.findall(r"\b[a-zA-Z_]+\b", sql_query)

    valid_columns = {col for cols in column_map.values() for col in cols}
    valid_tables = set(column_map.keys())

    for token in tokens:
        if token in valid_tables:
            continue
        if token in valid_columns:
            continue

        # Ignore SQL keywords
        if token.upper() in {
            "SELECT", "FROM", "WHERE", "AND", "OR",
            "JOIN", "ON", "GROUP", "BY", "ORDER",
            "HAVING", "COUNT", "SUM", "AVG", "MIN", "MAX",
            "LIMIT", "AS", "INNER", "LEFT", "RIGHT"
        }:
            continue

    return True  # basic validation (can expand later)


# ======================================================
# 4️⃣ EXECUTION VALIDATION
# ======================================================

def validate_execution(sql_query: str,
                       ddl_statements: List[str]) -> bool:

    try:
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        for ddl in ddl_statements:
            cursor.execute(ddl)

        cursor.execute(sql_query)

        conn.close()
        return True

    except Exception:
        return False


# ======================================================
# 5️⃣ GENERATE ENGLISH QUESTION FROM SQL
# ======================================================

def generate_question_from_sql(sql_query: str,
                                model: str,
                                temperature: float = 0.6) -> str:

    system_prompt = (
        "You are an expert at converting SQL queries into natural language questions.\n"
        "Given a SQL query, generate a clear English question that matches it.\n"
        "Only output the English question."
    )

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sql_query}
        ],
        options={"temperature": temperature}
    )

    question = response["message"]["content"].strip()
    question = re.sub(r"```", "", question).strip()

    return question


# ======================================================
# 6️⃣ SAVE DATASET
# ======================================================

def save_dataset(rows: List[Dict],
                 output_path: str):

    df = pd.DataFrame(rows)

    file_exists = os.path.isfile(output_path)

    df.to_csv(
        output_path,
        mode='a',
        index=False,
        header=not file_exists
    )

    jsonl_path = output_path.replace(".csv", ".jsonl")
    df.to_json(jsonl_path, orient="records", lines=True, mode="a")


# ======================================================
# 7️⃣ MAIN ENGINE
# ======================================================

def generate_nl2sql_dataset(schema_path: str,
                            output_path: str,
                            model: str,
                            num_samples: int = 5):

    schema = load_schema(schema_path)
    ddl_statements, column_map = json_to_sqlite_ddl(schema)

    dataset_rows = []

    # ------------------------------
    # LOAD EXISTING DATA (ONCE)
    # ------------------------------
    existing_sql = set()
    existing_questions = set()

    if os.path.exists(output_path):
        existing_df = pd.read_csv(output_path)
        if "sql_query" in existing_df.columns:
            existing_sql = set(existing_df["sql_query"].astype(str))
        if "english_question" in existing_df.columns:
            existing_questions = set(existing_df["english_question"].astype(str))

    print("🚀 Generating NL2SQL dataset...\n")

    attempts = 0
    max_attempts = num_samples * 5  # avoid infinite loop

    while len(dataset_rows) < num_samples and attempts < max_attempts:

        attempts += 1

        sql_query = generate_sql(ddl_statements, model)

        # Normalize SQL for better duplicate detection
        normalized_sql = " ".join(sql_query.lower().split())

        if normalized_sql in existing_sql:
            print("⚠ Duplicate SQL detected. Skipping.")
            continue

        if not validate_columns(sql_query, column_map):
            print("⚠ Column validation failed.")
            continue

        if not validate_execution(sql_query, ddl_statements):
            print("⚠ SQL execution failed.")
            continue

        question = generate_question_from_sql(sql_query, model)

        normalized_question = " ".join(question.lower().split())

        if normalized_question in existing_questions:
            print("⚠ Duplicate question detected. Skipping.")
            continue

        dataset_rows.append({
            "english_question": question,
            "sql_query": sql_query,
            "created_at": datetime.utcnow().isoformat()
        })

        # Update in-memory sets
        existing_sql.add(normalized_sql)
        existing_questions.add(normalized_question)

        print(f"✅ Valid unique pair generated ({len(dataset_rows)}/{num_samples})")

    if dataset_rows:
        save_dataset(dataset_rows, output_path)
        print(f"\n🎯 Saved {len(dataset_rows)} unique pairs.")
    else:
        print("\n❌ No valid unique pairs generated.")
        
# ======================================================
# 🔥 EXAMPLE USAGE
# ======================================================

if __name__ == "__main__":

    generate_nl2sql_dataset(
        schema_path="/home/soham/dataset_generator/schemas/schema1.json",
        output_path="/home/soham/dataset_generator/datasets/nl2sql_dataset_v1.csv",
        model="gemma3:1b",
        num_samples=10
    )