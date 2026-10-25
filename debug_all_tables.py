import csv, sqlite3
from pathlib import Path

evidence_files = {}
with open('dataset/evidence_files.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        evidence_files[row['file_id']] = row

sql_files = [(fid, ef['file_path']) for fid, ef in evidence_files.items() if ef['file_path'].endswith('.sql')]
for fid, fp in sql_files:
    file_path = Path('dataset') / fp
    conn = sqlite3.connect(':memory:')
    with open(file_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    for table in tables:
        cursor = conn.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        if rows:
            print(f'{fid} | {table} | {len(rows)} rows | columns={columns}')
            print(f'  Sample: {dict(zip(columns, rows[0]))}')
    conn.close()
