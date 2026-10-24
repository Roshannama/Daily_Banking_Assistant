"""End-to-end contract checks against the supplied synthetic banking database."""
import shutil
import sqlite3
from time import time

import pytest
from fastapi.testclient import TestClient
from app.api.main import create_app
from app.config import ROOT, Settings
from app.data.securebank_dataset_repository import SecureBankDatasetRepository
from app.models import Plan, ToolCall
from app.service import BankingService
from app.tools.gateway import Grant, scope
from app.tools.registry import REGISTRY, normalize_plan

DATASET = ROOT / 'runtime' / 'data' / 'securebank_demo.db'


@pytest.mark.skipif(not DATASET.is_file(), reason='Supplied local dataset copy is not installed')
def test_api_auth_and_all_banking_tools_on_supplied_dataset(tmp_path, encoded, credential):
    db = tmp_path / 'securebank_demo.db'
    shutil.copy2(DATASET, db)
    with sqlite3.connect(db) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS account_security (
            account_id TEXT PRIMARY KEY REFERENCES accounts(account_id) ON DELETE CASCADE,
            pin_hash TEXT, pin_updated_at TEXT,
            CHECK(pin_hash IS NULL OR pin_hash LIKE '$argon2id$%')
        )''')
        con.execute('''INSERT OR IGNORE INTO account_security(account_id)
            SELECT account_id FROM accounts''')
        con.execute('''UPDATE account_security SET pin_hash=? WHERE account_id IN
            (SELECT account_id FROM accounts WHERE customer_id='C1001')''', (encoded,))
        card = con.execute("SELECT card_id FROM cards WHERE customer_id='C1001' AND card_type='debit' AND status='active' LIMIT 1").fetchone()[0]
        transaction = con.execute('''SELECT t.transaction_id FROM transactions t JOIN accounts a USING(account_id)
            LEFT JOIN disputes d ON d.transaction_id=t.transaction_id AND d.status IN ('open','under_review')
            WHERE a.customer_id='C1001' AND d.dispute_id IS NULL LIMIT 1''').fetchone()[0]

    settings = Settings(repository='securebank_dataset', database_path=str(db), demo_pin_hash=encoded)
    repository = SecureBankDatasetRepository(str(db), encoded)
    service = BankingService(settings=settings, repository=repository, audit_path=tmp_path / 'audit.jsonl')
    with TestClient(create_app(service)) as client:
        assert client.get('/health').json()['repository'] == 'securebank_dataset'
        assert len(client.get('/dev/customers').json()['customer_ids']) == 50
        token = client.post('/dev/session', json={'customer_id': 'C1001'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        cid = client.post('/conversations', headers=headers).json()['conversation_id']

        faq = client.post('/chat', headers=headers, json={'conversation_id': cid, 'message': 'What is UPI?'}).json()
        assert faq['citations'] and faq['answer_type'] != 'pin_required'
        protected = client.post('/chat', headers=headers, json={'conversation_id': cid, 'message': 'My balance'}).json()
        assert protected['answer_type'] == 'pin_required'
        verified = client.post('/verify-pin', headers=headers,
                               json={'request_id': protected['request_id'], 'pin': credential}).json()
        assert verified['answer_type'] == 'retrieved_fact'

        calls = {
            'get_balance': ToolCall(name='get_balance'),
            'get_accounts': ToolCall(name='get_accounts'),
            'get_transactions': ToolCall(name='get_transactions'),
            'analyze_expenses': ToolCall(name='analyze_expenses', period='current_month'),
            'calculate_remaining_funds': ToolCall(name='calculate_remaining_funds'),
            'get_payment_status': ToolCall(name='get_payment_status'),
            'get_upcoming_payments': ToolCall(name='get_upcoming_payments'),
            'get_card_details': ToolCall(name='get_card_details'),
            'get_credit_card_details': ToolCall(name='get_credit_card_details'),
            'block_card': ToolCall(name='block_card', resource_id=card),
            'get_loan_details': ToolCall(name='get_loan_details'),
            'check_offer_eligibility': ToolCall(name='check_offer_eligibility'),
            'fraud_verification': ToolCall(name='fraud_verification'),
            'create_dispute': ToolCall(name='create_dispute', resource_id=transaction),
        }
        for name, call in calls.items():
            plan = Plan(intent='test', selected_agents=[], required_tools=[call], requires_rag=False,
                        requires_pin=True, requires_confirmation=REGISTRY[name][1])
            normalize_plan(plan)
            digest = scope(plan)
            result = service.gateway.execute('C1001', token, plan,
                Grant('C1001', token, digest, time() + 30), digest if plan.requires_confirmation else None,
                f'integration-{name}')
            assert result and result[0]['tool'] == name

    # Both write workflows ran against a disposable database copy.
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT status FROM cards WHERE card_id=?', (card,)).fetchone()[0] == 'blocked'
        assert con.execute('SELECT COUNT(*) FROM disputes WHERE transaction_id=?', (transaction,)).fetchone()[0] == 1
