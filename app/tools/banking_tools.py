from datetime import timedelta
from app.data.repository import RepositoryError

def run_tool(repo, customer, call, key):
    name, resource = call.name, call.resource_id
    def rows(kind):
        result = repo.records(customer, kind)
        if resource:
            result = [r for r in result if r.get('id') == resource or r.get('transaction_id') == resource or r.get('merchant', '').lower() == resource.lower()]
        return result
    def transactions():
        data = rows('transactions')
        if call.period == 'current_month':
            today = repo.today if hasattr(repo, 'today') else __import__('datetime').date.today()
            data = [r for r in data if r['date'][:7] == str(today)[:7]]
        return data
    if name in ('get_balance', 'get_accounts'):
        data = rows('accounts')
    elif name == 'get_customer_profile':
        data = rows('profile')
    elif name in ('get_transactions', 'get_payment_status'):
        data = transactions()
    elif name == 'analyze_expenses':
        txns = transactions(); categories = {}
        for t in txns:
            if t['status'] == 'success' and t['direction'] == 'debit':
                categories[t['category']] = categories.get(t['category'], 0) + t['amount_paise']
        income = sum(t['amount_paise'] for t in txns if t['status']=='success' and t['direction']=='credit')
        upcoming = sum(r['amount_paise'] for r in repo.records(customer,'upcoming'))
        data = [{'total_paise': sum(categories.values()), 'income_paise':income, 'upcoming_paise':upcoming, 'net_after_obligations_paise':income-sum(categories.values())-upcoming, 'categories_paise': categories, 'period': call.period, 'observation': 'Review discretionary spending against your savings goal. Net income after expenses and recorded obligations is an estimate, not your account balance or investment advice.'}]
    elif name == 'calculate_remaining_funds':
        accounts = repo.records(customer, 'accounts')
        if not accounts:
            return {'status': 'not_found', 'data': []}
        obligations = repo.records(customer, 'upcoming')
        balance = sum(r['balance_paise'] for r in accounts)
        total = sum(r['amount_paise'] for r in obligations)
        data = [{'balance_paise': balance, 'obligations_paise': total, 'remaining_paise': balance-total, 'note': 'Estimate covering all recorded upcoming obligations; future income is excluded.'}]
    elif name == 'get_upcoming_payments':
        data = rows('upcoming')
        if call.period == 'this_week':
            today = repo.today if hasattr(repo, 'today') else __import__('datetime').date.today()
            data = [r for r in data if str(today) <= r['due_date'] <= str(today+timedelta(days=7))]
    elif name in ('get_card_details', 'get_credit_card_details'):
        data = rows('cards')
        if name == 'get_credit_card_details':
            data = [r for r in data if r['type'] == 'credit']
    elif name == 'get_loan_details':
        data = rows('loans')
    elif name == 'check_offer_eligibility':
        consent = repo.records(customer, 'consent')
        if not consent or not consent[0]['personalized_offers']:
            return {'status': 'consent_required', 'data': []}
        data = rows('offers')
    elif name == 'fraud_verification':
        data = rows('fraud')
    elif name == 'block_card':
        return repo.block_card(customer, resource, key)
    elif name == 'create_dispute':
        return repo.create_dispute(customer, resource, key)
    else:
        raise RepositoryError('Tool not available')
    return {'status': 'ok' if data else 'not_found', 'data': data}
