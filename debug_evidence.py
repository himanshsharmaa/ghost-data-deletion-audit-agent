import csv, json, sqlite3, re
from pathlib import Path
from datetime import datetime

EVIDENCE_DIR = Path('dataset/evidence')

evidence_files = {}
with open('dataset/evidence_files.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        evidence_files[row['file_id']] = row

sql_files = [(fid, ef['file_path']) for fid, ef in evidence_files.items() if ef['file_path'].endswith('.sql')]
print('SQL files:', len(sql_files))
for fid, fp in sql_files[:5]:
    print(f'  {fid}: {fp}')

if sql_files:
    fid, fp = sql_files[0]
    file_path = EVIDENCE_DIR / fp
    print(f'\nParsing {file_path}...')
    conn = sqlite3.connect(':memory:')
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    conn.executescript(sql_content)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print('Tables:', tables)
    for table in tables[:3]:
        cursor = conn.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        print(f'  {table}: {len(rows)} rows, columns={columns}')
        if rows:
            print(f'    First row: {dict(zip(columns, rows[0]))}')
    conn.close()

# Check JSON files
json_files = [(fid, ef['file_path']) for fid, ef in evidence_files.items() if ef['file_path'].endswith('.json')]
print('\nJSON files:', len(json_files))
for fid, fp in json_files[:5]:
    print(f'  {fid}: {fp}')

# Check log files
log_files = [(fid, ef['file_path']) for fid, ef in evidence_files.items() if ef['file_path'].endswith('.log')]
print('\nLog files:', len(log_files))
for fid, fp in log_files[:5]:
    print(f'  {fid}: {fp}')
