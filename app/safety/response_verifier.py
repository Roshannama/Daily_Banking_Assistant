"""Positive result schemas: unexpected fields are never serialized to a customer."""
from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError
import re

FIELDS = {
 'get_balance': {'id','balance_paise','currency','last4','type'},
 'get_accounts': {'id','account_number','balance_paise','currency','last4','type'},
 'get_customer_profile': {'id','full_name'},
 'get_transactions': {'id','merchant','amount_paise','status','direction','category','date','reference','reason'},
 'get_payment_status': {'id','merchant','amount_paise','status','direction','category','date','reference','reason'},
 'get_card_details': {'id','type','last4','status','amount_due_paise','due_date','repayment_options'},
 'get_credit_card_details': {'id','type','last4','status','amount_due_paise','due_date','repayment_options'},
 'get_upcoming_payments': {'id','label','amount_paise','due_date'},
 'get_loan_details': {'id','status','outstanding_paise','emi_paise','next_due_date'},
 'check_offer_eligibility': {'id','product','eligible','decision_source','final_approval_required'},
 'fraud_verification': {'id','transaction_id','risk_level','reason','explanation','status','conclusion'},
 'analyze_expenses': {'total_paise','income_paise','upcoming_paise','net_after_obligations_paise','categories_paise','period','observation'},
 'calculate_remaining_funds': {'balance_paise','obligations_paise','remaining_paise','note'},
}
REQUIRED = {
 'get_balance': {'id','balance_paise'}, 'get_accounts': {'id','balance_paise'},
 'get_customer_profile': {'id','full_name'},
 'get_transactions': {'id','amount_paise','status'}, 'get_payment_status': {'id','amount_paise','status'},
 'get_card_details': {'id','status','last4'}, 'get_credit_card_details': {'id','status','amount_due_paise','due_date'},
 'get_upcoming_payments': {'id','amount_paise','due_date'}, 'get_loan_details': {'id','emi_paise','outstanding_paise'},
 'check_offer_eligibility': {'id','eligible'}, 'fraud_verification': {'transaction_id','status'},
 'analyze_expenses': {'total_paise','categories_paise'}, 'calculate_remaining_funds': {'balance_paise','obligations_paise','remaining_paise'},
}

def check_value(value):
    if isinstance(value,str):
        if len(value)>500 or re.search(r'\b\d{12,19}\b|\$argon2|\bBearer\s+|\bsk-[A-Za-z0-9]+',value) or re.search(r'(password|pin|secret|token)\s*[:=]',value,re.I):
            raise ValueError('Unsafe tool value')
    elif isinstance(value,list):
        for item in value: check_value(item)
    elif isinstance(value,dict):
        for key,item in value.items(): check_value(key); check_value(item)
    elif value is not None and type(value) not in (int,bool):
        raise ValueError('Unexpected value type')

def validate_result(tool, result):
    if not isinstance(result, dict):
        raise ValueError('Unexpected tool result')
    if tool in ('block_card','create_dispute'):
        if result.get('status') == 'not_found':
            return {'status':'not_found'}
        expected = 'blocked' if tool == 'block_card' else 'opened'
        fields = {'status','card_id'} if tool == 'block_card' else {'status','dispute_id','transaction_id'}
        if result.get('status') != expected or not fields.issubset(result):
            raise ValueError('Action result is unverified')
        clean={k: result[k] for k in fields}
        check_value(clean)
        return clean
    if result.get('status') not in ('ok','not_found','consent_required') or not isinstance(result.get('data'), list):
        raise ValueError('Invalid tool result schema')
    data = []
    for row in result['data']:
        if not isinstance(row,dict) or not REQUIRED[tool].issubset(row):
            raise ValueError('Missing required tool fields')
        clean = {k:v for k,v in row.items() if k in FIELDS[tool]}
        check_value(clean)
        for k,v in clean.items():
            if k.endswith('_paise') and k != 'categories_paise' and type(v) is not int:
                raise ValueError('Money must be integer paise')
            if isinstance(v,str) and len(v) > 500:
                raise ValueError('Unexpected data size')
            if isinstance(v,str) and (re.search(r'\b\d{12,19}\b|\$argon2|\bBearer\s+|\bsk-[A-Za-z0-9]+',v) or re.search(r'(password|pin|secret|token)\s*[:=]',v,re.I)):
                raise ValueError('Sensitive value returned by tool')
        if 'last4' in clean and (not clean['last4'].isdigit() or len(clean['last4']) != 4):
            raise ValueError('Identifier is not masked')
        if 'account_number' in clean:
            number = clean['account_number']
            if not isinstance(number, str) or not re.search(r'[*xX•]', number) or len(re.sub(r'\D', '', number)) != 4:
                raise ValueError('Account number is not safely masked')
        if tool == 'fraud_verification':
            if 'risk_level' in clean and clean['risk_level'] not in ('low', 'medium', 'high'):
                raise ValueError('Unknown fraud risk level')
            if 'status' in clean and clean['status'] not in ('open', 'under_investigation', 'confirmed_fraud', 'cleared', 'review_available'):
                raise ValueError('Unknown fraud alert status')
        if tool == 'calculate_remaining_funds' and clean['balance_paise']-clean['obligations_paise'] != clean['remaining_paise']:
            raise ValueError('Calculation mismatch')
        if tool == 'analyze_expenses' and (any(type(v) is not int for v in clean['categories_paise'].values()) or sum(clean['categories_paise'].values()) != clean['total_paise']):
            raise ValueError('Expense calculation mismatch')
        if tool == 'analyze_expenses' and 'net_after_obligations_paise' in clean and clean['income_paise']-clean['total_paise']-clean['upcoming_paise']!=clean['net_after_obligations_paise']:
            raise ValueError('Savings calculation mismatch')
        data.append(clean)
    return {'status':result['status'], 'data':data}
