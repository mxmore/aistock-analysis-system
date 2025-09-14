import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Connect to postgres system db to check/create target db
def ensure_db_exists():
    conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database {DB_NAME} created.")
        else:
            print(f"Database {DB_NAME} already exists.")
    conn.close()

# Run init.sql to create tables etc.
def run_sql(sql_path):
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print(f"Executed {sql_path} successfully.")

if __name__ == "__main__":
    ensure_db_exists()
    sql_file = os.path.join(os.path.dirname(__file__), "init.sql")
    run_sql(sql_file)
