import os
from pathlib import Path
import psycopg
from psycopg import sql
passwords={'gateway_reader':os.environ['READER_DATABASE_PASSWORD'],'gateway_ingest':os.environ['INGEST_DATABASE_PASSWORD']}
if passwords['gateway_reader']==passwords['gateway_ingest']:raise ValueError('Reader and ingestion passwords must differ')
with psycopg.connect(os.environ['ADMIN_DATABASE_URL'],autocommit=True) as c:
    for name,password in passwords.items():
        if not c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(name,)).fetchone():
            c.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(name),sql.Literal(password)))
        else:c.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(name),sql.Literal(password)))
    c.execute(Path('sql/schema.sql').read_text())
