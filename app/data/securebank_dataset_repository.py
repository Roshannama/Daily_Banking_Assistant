"""Adapter for the supplied SecureBank Demo Bank SQLite dataset.

The source schema remains intact. All reads include an ownership predicate or
join through an owned account. This adapter is for synthetic local demos only.
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from app.data.repository import RepositoryError


class SecureBankDatasetRepository:
    def __init__(self, path, demo_pin_hash=''):
        if not path or not Path(path).is_file():
            raise RepositoryError('SecureBank dataset database file is unavailable')
        self.path = str(path)
        self.demo_pin_hash = demo_pin_hash
        try:
            with self.session() as con:
                names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'customers', 'accounts', 'transactions', 'cards', 'loans', 'users'}.issubset(names):
                    raise RepositoryError('Unrecognized SecureBank dataset schema')
        except sqlite3.Error as exc:
            raise RepositoryError('SecureBank dataset database cannot be opened') from exc

    def connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        return con

    @contextmanager
    def session(self):
        con = self.connect()
        try:
            with con:
                yield con
        finally:
            con.close()

    def _all(self, sql, args=()):
        try:
            with self.session() as con:
                return [dict(r) for r in con.execute(sql, args)]
        except sqlite3.Error as exc:
            raise RepositoryError('SecureBank dataset query failed') from exc

    def records(self, customer, kind):
        if kind == 'profile':
            rows = self._all('SELECT customer_id,full_name FROM customers WHERE customer_id=?', (customer,))
            return [dict(id=r['customer_id'], full_name=r['full_name']) for r in rows]
        if kind == 'accounts':
            rows = self._all('SELECT account_id,account_number_masked,account_type,currency,balance_paise,available_balance_paise,account_status FROM accounts WHERE customer_id=?', (customer,))
            return [dict(id=r['account_id'], account_number=r['account_number_masked'], type=r['account_type'], currency=r['currency'], balance_paise=r['available_balance_paise'], ledger_balance_paise=r['balance_paise'], status=r['account_status'], last4=r['account_number_masked'][-4:]) for r in rows]
        if kind == 'transactions':
            rows = self._all('''SELECT t.*, u.status AS upi_status, u.failure_reason AS upi_failure_reason
                FROM transactions t JOIN accounts a ON a.account_id=t.account_id
                LEFT JOIN upi_payments u ON u.transaction_id=t.transaction_id
                WHERE a.customer_id=? ORDER BY t.transaction_date DESC''', (customer,))
            status_map = {'completed': 'success', 'pending': 'pending', 'failed': 'failed', 'reversed': 'reversed'}
            return [dict(id=r['transaction_id'], merchant=r['merchant'], amount_paise=r['amount_paise'],
                         direction=r['direction'], status=status_map.get(r['status'], r['status']),
                         date=r['transaction_date'], category=r['category'], reference=r['reference_number'],
                         reason=r['upi_failure_reason'], payment_method=r['payment_method'],
                         payment_status=r['upi_status']) for r in rows]
        if kind == 'upcoming':
            rows = self._all('SELECT payment_id,payee,amount_paise,due_date,payment_type,status FROM upcoming_payments WHERE customer_id=? ORDER BY due_date', (customer,))
            return [dict(id=r['payment_id'], label=r['payee'], amount_paise=r['amount_paise'], due_date=r['due_date'], type=r['payment_type'], status=r['status']) for r in rows]
        if kind == 'cards':
            rows = self._all('''SELECT c.*, s.statement_amount_paise, s.amount_paid_paise, s.due_date
                FROM cards c LEFT JOIN credit_card_statements s ON s.card_id=c.card_id
                AND s.statement_date=(SELECT MAX(s2.statement_date) FROM credit_card_statements s2 WHERE s2.card_id=c.card_id)
                WHERE c.customer_id=? ORDER BY c.card_id''', (customer,))
            result = []
            for r in rows:
                due = max(0, (r['statement_amount_paise'] or 0) - (r['amount_paid_paise'] or 0))
                card = dict(id=r['card_id'], type=r['card_type'], last4=r['last_four_digits'], status=r['status'],
                            network=r['network'], variant=r['card_variant'], credit_limit_paise=r['credit_limit_paise'],
                            available_limit_paise=r['available_limit_paise'])
                if r['card_type'] == 'credit':
                    card.update(amount_due_paise=due, due_date=r['due_date'])
                result.append(card)
            return result
        if kind == 'loans':
            rows = self._all('SELECT * FROM loans WHERE customer_id=? ORDER BY loan_id', (customer,))
            return [dict(id=r['loan_id'], type=r['loan_type'], status=r['loan_status'], principal_paise=r['principal_paise'],
                         outstanding_paise=r['outstanding_balance_paise'], emi_paise=r['emi_amount_paise'],
                         next_due_date=r['next_emi_date'], interest_rate=r['annual_interest_rate'], remaining_months=r['remaining_months']) for r in rows]
        if kind == 'fraud':
            rows = self._all('SELECT transaction_id,risk_level,reason_code,explanation,status FROM fraud_alerts WHERE customer_id=? ORDER BY created_at DESC', (customer,))
            return [dict(id=r['transaction_id'], transaction_id=r['transaction_id'], risk_level=r['risk_level'], reason=r['reason_code'], explanation=r['explanation'], status=r['status']) for r in rows]
        if kind == 'offers':
            rows = self._all('''SELECT co.offer_id, po.offer_name, co.eligibility_status, co.reason_code
                FROM customer_offers co JOIN product_offers po ON po.offer_id=co.offer_id
                WHERE co.customer_id=? AND po.offer_status='active' ORDER BY co.offer_id''', (customer,))
            return [dict(id=r['offer_id'], product=r['offer_name'], eligible=r['eligibility_status']=='eligible', reason=r['reason_code']) for r in rows]
        if kind == 'consent':
            rows = self._all("SELECT status FROM consents WHERE customer_id=? AND purpose='personalized_offers'", (customer,))
            return [dict(personalized_offers=bool(rows and rows[0]['status']=='granted'))]
        raise RepositoryError('Unknown record type')

    def pin_hash(self, customer):
        # Dataset login password hashes are not PINs. Each bank account has an
        # independent Argon2 PIN hash in account_security. The current fixture
        # has one account per customer; fail closed if a customer owns multiple
        # accounts because the login flow has not selected an account yet.
        security_table = self._all(
            "SELECT 1 AS found FROM sqlite_master WHERE type='table' AND name='account_security'"
        )
        if not security_table:
            # Compatibility for an unmigrated development database only.
            exists = self._all('SELECT 1 AS found FROM customers WHERE customer_id=?', (customer,))
            return self.demo_pin_hash if exists else None
        rows = self._all('''SELECT s.pin_hash FROM accounts a
            LEFT JOIN account_security s ON s.account_id=a.account_id
            WHERE a.customer_id=? ORDER BY a.account_id''', (customer,))
        if len(rows) != 1:
            return None
        return rows[0]['pin_hash']

    def customer_ids(self):
        rows = self._all('SELECT customer_id FROM customers ORDER BY customer_id')
        return [r['customer_id'] for r in rows]

    def block_card(self, customer, resource, key):
        try:
            with self.session() as con:
                con.execute('BEGIN IMMEDIATE')
                row = con.execute('SELECT status FROM cards WHERE customer_id=? AND card_id=?', (customer, resource)).fetchone()
                if not row:
                    return {'status': 'not_found'}
                if row['status'] != 'blocked':
                    con.execute("UPDATE cards SET status='blocked', blocked_at=datetime('now'), block_reason='customer_request' WHERE customer_id=? AND card_id=?", (customer, resource))
                verified = con.execute('SELECT status FROM cards WHERE customer_id=? AND card_id=?', (customer, resource)).fetchone()
                if not verified or verified['status'] != 'blocked':
                    raise RepositoryError('Card block write verification failed')
                return {'status': 'blocked', 'card_id': resource}
        except sqlite3.Error as exc:
            raise RepositoryError('Card block operation failed') from exc

    def create_dispute(self, customer, resource, key):
        try:
            with self.session() as con:
                con.execute('BEGIN IMMEDIATE')
                owned = con.execute('''SELECT t.transaction_id FROM transactions t JOIN accounts a ON a.account_id=t.account_id
                    WHERE a.customer_id=? AND t.transaction_id=?''', (customer, resource)).fetchone()
                if not owned:
                    return {'status': 'not_found'}
                existing = con.execute("SELECT dispute_id FROM disputes WHERE customer_id=? AND transaction_id=? AND status IN ('open','under_review')", (customer, resource)).fetchone()
                if existing:
                    return {'status': 'opened', 'dispute_id': existing['dispute_id'], 'transaction_id': resource}
                dispute_id = 'DSP' + uuid.uuid4().hex[:12].upper()
                now = __import__('datetime').datetime.now().isoformat(timespec='seconds')
                con.execute('INSERT INTO disputes(dispute_id,customer_id,transaction_id,reason,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                            (dispute_id, customer, resource, 'unrecognised_transaction', 'open', now, now))
                return {'status': 'opened', 'dispute_id': dispute_id, 'transaction_id': resource}
        except sqlite3.Error as exc:
            raise RepositoryError('Dispute creation failed') from exc

    def audit(self, event):
        try:
            with self.session() as con:
                con.execute('''INSERT INTO audit_logs(trace_id,customer_id,action_type,tool_name,resource_type,resource_id,
                    authorization_result,action_status,safe_parameters,created_at) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))''',
                    (event.get('trace_id', 'unknown'), event.get('customer_id'), event.get('event', 'assistant_event'),
                     event.get('tool'), event.get('resource_type'), event.get('resource_id'),
                     'denied' if event.get('authorization') == 'denied' else 'allowed',
                     event.get('action_status', 'recorded'), json.dumps(event, separators=(',', ':'))))
        except sqlite3.Error as exc:
            raise RepositoryError('Audit write failed') from exc
