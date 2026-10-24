"""Opt-in canonical integration contract, never creates or migrates teammate tables."""
import json
import sqlite3
from pathlib import Path
from app.data.repository import RepositoryError

class SQLiteBankingRepository:
    def __init__(self, path):
        if not Path(path).is_file():
            raise RepositoryError('Supply an existing integration database')
        self.path = path
        with self.connect() as con:
            columns = {r[1] for r in con.execute('PRAGMA table_info(banking_records)')}
            if not {'customer_id', 'kind', 'resource_id', 'payload'}.issubset(columns):
                raise RepositoryError('Database mapping required: see docs/database_contract.md')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def records(self, customer, kind):
        try:
            with self.connect() as con:
                return [json.loads(r[0]) for r in con.execute('SELECT payload FROM banking_records WHERE customer_id=? AND kind=?', (customer, kind))]
        except (sqlite3.Error, ValueError) as e:
            raise RepositoryError('Database unavailable') from e

    def pin_hash(self, customer):
        with self.connect() as con:
            row = con.execute('SELECT pin_hash FROM banking_customers WHERE customer_id=?', (customer,)).fetchone()
            return row[0] if row else None

    def block_card(self, customer, resource, key):
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("SELECT payload FROM banking_records WHERE customer_id=? AND kind='cards' AND resource_id=?", (customer, resource)).fetchone()
            if not row:
                return {'status': 'not_found'}
            payload = json.loads(row[0]); payload['status'] = 'blocked'
            con.execute("UPDATE banking_records SET payload=? WHERE customer_id=? AND kind='cards' AND resource_id=?", (json.dumps(payload), customer, resource))
            verified = con.execute("SELECT payload FROM banking_records WHERE customer_id=? AND kind='cards' AND resource_id=?", (customer, resource)).fetchone()
            if json.loads(verified[0])['status'] != 'blocked':
                raise RepositoryError('Write verification failed')
            return {'status': 'blocked', 'card_id': resource}

    def create_dispute(self, customer, resource, key):
        import uuid
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            if not con.execute("SELECT 1 FROM banking_records WHERE customer_id=? AND kind='transactions' AND resource_id=?", (customer, resource)).fetchone():
                return {'status': 'not_found'}
            con.execute('INSERT OR IGNORE INTO banking_disputes(customer_id,transaction_id,dispute_id,idempotency_key) VALUES(?,?,?,?)', (customer, resource, 'DSP'+uuid.uuid4().hex, key))
            row = con.execute('SELECT dispute_id FROM banking_disputes WHERE customer_id=? AND transaction_id=?', (customer, resource)).fetchone()
            return {'status': 'opened', 'dispute_id': row[0], 'transaction_id': resource}

    def audit(self, event):
        with self.connect() as con:
            con.execute('INSERT INTO banking_audit(event) VALUES(?)', (json.dumps(event),))
