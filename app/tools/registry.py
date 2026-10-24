REGISTRY = {
    'get_balance': ('account', False),
    'get_accounts': ('account', False),
    'get_customer_profile': ('account', False),
    'get_transactions': ('account', False),
    'analyze_expenses': ('account', False),
    'calculate_remaining_funds': ('account', False),
    'get_payment_status': ('payments', False),
    'get_upcoming_payments': ('payments', False),
    'get_card_details': ('cards', False),
    'get_credit_card_details': ('cards', False),
    'block_card': ('cards', True),
    'get_loan_details': ('loans', False),
    'check_offer_eligibility': ('loans', False),
    'fraud_verification': ('fraud', False),
    'create_dispute': ('fraud', True),
}

def normalize_plan(plan):
    if len(plan.required_tools) > 6 or any(t.name not in REGISTRY for t in plan.required_tools):
        raise ValueError('Unknown tool or excessive tool plan')
    if len({t.name for t in plan.required_tools}) != len(plan.required_tools):
        raise ValueError('Duplicate tool')
    agents = sorted({REGISTRY[t.name][0] for t in plan.required_tools} | ({'knowledge'} if plan.requires_rag else set()))
    plan.selected_agents = agents or ['unsupported']
    plan.intent = 'mixed' if len(agents) > 1 else (agents[0] if agents else 'unsupported')
    plan.requires_pin = bool(plan.required_tools)
    plan.requires_confirmation = any(REGISTRY[t.name][1] for t in plan.required_tools)
    if plan.requires_confirmation and len(plan.required_tools) != 1:
        raise ValueError('Submit each write action as a separate request')
    for t in plan.required_tools:
        if t.name in ('block_card', 'create_dispute') and not t.resource_id:
            plan.missing_information = ['Specify the exact card ID or transaction ID. You can request your card details or transactions first.']
    return plan
