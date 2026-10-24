import hashlib
import json
import time
from dataclasses import dataclass
from app.tools.registry import normalize_plan
from app.tools.banking_tools import run_tool
from app.safety.response_verifier import validate_result

@dataclass
class Grant:
    customer: str
    token: str
    scope: str
    expires: float

def scope(plan):
    return hashlib.sha256(plan.model_dump_json().encode()).hexdigest()

class ToolGateway:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, customer, token, plan, grant, confirmed_scope, request_id):
        normalize_plan(plan)
        digest = scope(plan)
        if not grant or grant.customer != customer or grant.token != token or grant.scope != digest or grant.expires <= time.time():
            raise PermissionError('PIN authorization required for this operation')
        if plan.requires_confirmation and confirmed_scope != digest:
            raise PermissionError('Exact action confirmation required')
        if plan.missing_information:
            raise PermissionError('Resource is missing')
        results = []
        for call in plan.required_tools:
            # Repository always applies customer ownership in the query, never trusts a model identity.
            result = run_tool(self.repository, customer, call, request_id)
            clean = validate_result(call.name, result)
            if call.name=='block_card' and clean.get('status')=='blocked' and clean.get('card_id')!=call.resource_id:
                raise ValueError('Card action resource mismatch')
            if call.name=='create_dispute' and clean.get('status')=='opened' and clean.get('transaction_id')!=call.resource_id:
                raise ValueError('Dispute action resource mismatch')
            results.append({'tool': call.name, 'result': clean})
        return results
