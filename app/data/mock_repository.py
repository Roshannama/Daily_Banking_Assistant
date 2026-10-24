from copy import deepcopy
from datetime import date, timedelta
from threading import RLock
from app.data.repository import RepositoryError

class MockBankingRepository:
    """Synthetic in-memory banking records; resets on server restart."""
    def __init__(self, pin_hash='', today=None):
        self.today = today or date.today()
        self.hash = pin_hash
        self.lock = RLock()
        self.reads = []
        self.writes = []
        self.events = []
        self.disputes = {}
        self.data = {}
        for i in range(1, 11):
            c = f'C{1000+i}'
            self.data[c] = {
                'profile': [dict(id=c, full_name=f'Demo Customer {i}')],
                'accounts': [dict(id=f'ACC{i:04}', balance_paise=12500000+i*10000, currency='INR', last4=f'{4100+i}', type='savings')],
                'transactions': [
                    dict(id=f'TXN{i:04}A', merchant='Amazon', amount_paise=240000, status='failed', direction='debit', category='Shopping', date=str(self.today), reference=f'REF{i:04}A', reason='Beneficiary bank timeout'),
                    dict(id=f'TXN{i:04}B', merchant='Groceries', amount_paise=85000, status='success', direction='debit', category='Food', date=str(self.today-timedelta(days=1)), reference=f'REF{i:04}B', reason=None),
                    dict(id=f'TXN{i:04}C', merchant='Payroll', amount_paise=7500000, status='success', direction='credit', category='Income', date=str(self.today.replace(day=1)), reference=f'REF{i:04}C', reason=None),
                    dict(id=f'TXN{i:04}D', merchant='Metro', amount_paise=32000, status='success', direction='debit', category='Transport', date=str(self.today), reference=f'REF{i:04}D', reason=None)],
                'upcoming': [dict(id=f'BILL{i:04}', label='Utilities', amount_paise=450000, due_date=str(self.today+timedelta(days=2))), dict(id=f'EMI{i:04}', label='Home loan EMI', amount_paise=2500000, due_date=str(self.today+timedelta(days=5))), dict(id=f'DUE{i:04}', label='Credit card statement', amount_paise=550000, due_date=str(self.today+timedelta(days=10)))],
                'cards': [dict(id=f'CARD{i:04}D', type='debit', last4=f'{5100+i}', status='active'), dict(id=f'CARD{i:04}C', type='credit', last4=f'{6100+i}', status='active', amount_due_paise=550000, due_date=str(self.today+timedelta(days=10)), repayment_options=['Bank app payment', 'Autopay'])],
                'loans': [dict(id=f'LOAN{i:04}', status='active', outstanding_paise=180000000, emi_paise=2500000, next_due_date=str(self.today+timedelta(days=5)))],
                'fraud': [dict(transaction_id=f'TXN{i:04}B', status='review_available', conclusion='A fraud determination requires bank review.')],
                'offers': [dict(id=f'OFFER{i:04}', product='Personal loan', eligible=i%2==1, decision_source='Synthetic approved eligibility fixture', final_approval_required=True)],
                'consent': [dict(personalized_offers=i%2==1)],
            }

    def records(self, customer, kind):
        with self.lock:
            self.reads.append((customer, kind))
            if customer not in self.data:
                return []
            if kind not in self.data[customer]:
                raise RepositoryError('Unknown record type')
            return deepcopy(self.data[customer][kind])

    def pin_hash(self, customer):
        return self.hash if customer in self.data else None

    def customer_ids(self):
        return sorted(self.data)

    def block_card(self, customer, resource, key):
        with self.lock:
            card = next((r for r in self.data.get(customer, {}).get('cards', []) if r['id'] == resource), None)
            if not card:
                return {'status': 'not_found'}
            card['status'] = 'blocked'
            self.writes.append((customer, 'block_card', resource, key))
            return {'status': 'blocked', 'card_id': resource}

    def create_dispute(self, customer, resource, key):
        with self.lock:
            txn = next((r for r in self.data.get(customer, {}).get('transactions', []) if r['id'] == resource), None)
            if not txn:
                return {'status': 'not_found'}
            k = (customer, resource)
            if k not in self.disputes:
                self.disputes[k] = {'status': 'opened', 'dispute_id': f'DSP{len(self.disputes)+1:06}', 'transaction_id': resource}
                self.writes.append((customer, 'create_dispute', resource, key))
            return deepcopy(self.disputes[k])

    def audit(self, event):
        self.events.append(deepcopy(event))
