from app.models import ToolCall
from app.tools.banking_tools import run_tool
from datetime import date

def test_failed_debits_excluded_and_integer_calculation(service):
    service.repository.today=date(2026,10,24)
    for t in service.repository.data['C1001']['transactions']:
        t['date']='2026-10-24'
    r=run_tool(service.repository,'C1001',ToolCall(name='analyze_expenses',period='current_month'),'test')['data'][0]
    assert r['total_paise']==117000 and r['income_paise']==7500000
    assert r['net_after_obligations_paise']==3883000
    remaining=run_tool(service.repository,'C1001',ToolCall(name='calculate_remaining_funds'),'test')['data'][0]
    assert remaining['remaining_paise']==9010000

def test_missing_customer_and_consent(service):
    assert run_tool(service.repository,'C9999',ToolCall(name='get_balance'),'test')['status']=='not_found'
    assert run_tool(service.repository,'C1002',ToolCall(name='check_offer_eligibility'),'test')['status']=='consent_required'
