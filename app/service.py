import json
import secrets
import time
from threading import RLock
from app.config import Settings
from app.auth.trusted_context import SessionStore
from app.auth.pin_verification import PinVerifier
from app.agents.supervisor import route
from app.agents.handlers import AGENTS
from app.tools.gateway import Grant, ToolGateway, scope
from app.data.mock_repository import MockBankingRepository
from app.data.sqlite_repository import SQLiteBankingRepository
from app.data.securebank_dataset_repository import SecureBankDatasetRepository
from app.monitoring.audit import Audit
from app.rag.retrieval import Retriever, generate_citations
from app.safety.guardrails import deny_reason, safe_history

class BankingService:
    def __init__(self, settings=None, repository=None, retriever=None, audit_path=None):
        self.settings = settings or Settings()
        if self.settings.mode != 'development':
            raise RuntimeError('Production disabled until verified upstream identity, persistent rate limits and shared session storage are integrated.')
        if repository is not None:
            self.repository = repository
        elif self.settings.repository == 'sqlite':
            self.repository = SQLiteBankingRepository(self.settings.database_path)
        elif self.settings.repository == 'securebank_dataset':
            self.repository = SecureBankDatasetRepository(self.settings.database_path, self.settings.demo_pin_hash)
        else:
            self.repository = MockBankingRepository(self.settings.pin_hash)
        self.sessions = SessionStore(self.settings, self.repository.customer_ids() if hasattr(self.repository, 'customer_ids') else None)
        self.pin = PinVerifier(self.repository, self.settings)
        self.gateway = ToolGateway(self.repository)
        self.retriever = retriever or Retriever(self.settings)
        self.audit = Audit(self.repository, audit_path)
        self.pending = {}
        self.lock = RLock()

    def conversation(self, token):
        session = self.sessions.get(token)
        cid = secrets.token_urlsafe(16)
        session.conversations[cid] = []
        return cid

    def history(self, token, cid):
        session = self.sessions.get(token)
        if cid not in session.conversations:
            raise PermissionError('Conversation does not belong to this session')
        return session.conversations[cid]

    def clear(self, token, cid):
        with self.lock:
            self.history(token,cid).clear()
            for rid in list(self.pending):
                p = self.pending[rid]
                if p['token']==token and p['cid']==cid:
                    del self.pending[rid]

    def result(self, trace, kind, answer, **extra):
        return dict(answer=answer, answer_type=kind, citations=[], tools_used=[], trace_id=trace, action_status='none', **extra)

    def save(self, token, cid, result):
        self.history(token,cid).append({'role':'assistant','response':result})
        return result

    def chat(self, token, cid, message):
        with self.lock:
            started = time.perf_counter()
            session = self.sessions.get(token)
            history = self.history(token,cid)
            trace = secrets.token_hex(12)
            history.append({'role':'user','content':safe_history(message)})
            denial = deny_reason(message, session.customer)
            if denial:
                self.audit.record(trace,session.customer,'request_denied',authorization='denied')
                return self.save(token,cid,self.result(trace,'refused',denial))
            try:
                plan = route(message,self.settings)
                for call in plan.required_tools:
                    AGENTS[__import__('app.tools.registry',fromlist=['REGISTRY']).REGISTRY[call.name][0]].validate(call)
                self.audit.record(trace,session.customer,'planned',agents=plan.selected_agents,tools=[t.name for t in plan.required_tools],authorization='pending' if plan.requires_pin else 'public')
            except Exception:
                self.audit.record(trace,session.customer,'planner_error',error_category='planner_unavailable')
                return self.save(token,cid,self.result(trace,'data_unavailable','The planner is unavailable. Please retry or contact bank support.'))
            if plan.missing_information:
                return self.save(token,cid,self.result(trace,'clarification_needed',' '.join(plan.missing_information)))
            if not plan.required_tools and not plan.requires_rag:
                return self.save(token,cid,self.result(trace,'refused','I can help with banking accounts, payments, cards, loans, fraud and approved FAQs. Please specify a banking request.'))
            rid = secrets.token_urlsafe(24)
            # Drop expired operations and bound pending memory per local process.
            self.pending = {k:v for k,v in self.pending.items() if v['expires']>time.time()}
            if len(self.pending)>=1000:
                return self.save(token,cid,self.result(trace,'data_unavailable','Too many pending requests. Please retry later.'))
            p = dict(token=token,customer=session.customer,cid=cid,query=message,plan=plan,trace=trace,expires=time.time()+self.settings.request_ttl,grant=None,confirmed_scope=None,started=started,done=False)
            self.pending[rid] = p
            if plan.requires_pin:
                result = self.result(trace,'pin_required','Verify your PIN to authorize this request. No protected banking records have been retrieved.',request_id=rid,operation=plan.model_dump(),requires_confirmation=plan.requires_confirmation)
                return self.save(token,cid,result)
            return self.execute(rid,p)

    def operation(self, token, rid):
        session = self.sessions.get(token)
        p = self.pending.get(rid)
        if not p or p['token']!=token or p['customer']!=session.customer or p['expires']<=time.time() or p['done']:
            raise PermissionError('Pending request is missing, expired or already consumed')
        return p

    def verify(self, token, rid, pin):
        with self.lock:
            p = self.operation(token,rid)
            outcome = self.pin.verify(p['customer'],pin)
            self.audit.record(p['trace'],p['customer'],'pin_verification',pin_outcome=outcome)
            if outcome!='verified':
                unavailable = ('No PIN is configured for this account. Run scripts/set_account_pins.py locally.'
                               if self.settings.repository == 'securebank_dataset'
                               else 'Demo PIN is not configured. Run scripts/set_demo_pin.py locally.')
                message = {'locked':'PIN verification is temporarily locked. Try again later.','invalid':'PIN verification failed.','unavailable':unavailable}[outcome]
                return self.result(p['trace'],'pin_required',message,request_id=rid)
            p['grant'] = Grant(p['customer'],token,scope(p['plan']),time.time()+self.settings.grant_ttl)
            if p['plan'].requires_confirmation:
                call = p['plan'].required_tools[0]
                result = self.result(p['trace'],'pending_confirmation',f'Confirm {call.name} for {call.resource_id}. This approval applies only to this operation.',request_id=rid,operation=p['plan'].model_dump())
                return self.save(token,p['cid'],result)
            return self.execute(rid,p)

    def confirm(self, token, rid, confirmed):
        with self.lock:
            p = self.operation(token,rid)
            self.audit.record(p['trace'],p['customer'],'confirmation',confirmation=confirmed)
            if not confirmed:
                p['done']=True
                return self.save(token,p['cid'],self.result(p['trace'],'refused','Action cancelled. No banking action was executed.'))
            p['confirmed_scope']=scope(p['plan'])
            return self.execute(rid,p)

    def execute(self, rid, p):
        try:
            results = self.gateway.execute(p['customer'],p['token'],p['plan'],p['grant'],p['confirmed_scope'],rid) if p['plan'].required_tools else []
            chunks = self.retriever.retrieve_relevant_chunks(p['query']) if p['plan'].requires_rag else []
            result = compose(p['trace'],results,chunks)
            self.audit.record(p['trace'],p['customer'],'completed',agents=p['plan'].selected_agents,tools=[r['tool'] for r in results],authorization='granted' if results else 'public',source_ids=[c['chunk_id'] for c in chunks],action_status=result['action_status'],latency_ms=round((time.perf_counter()-p['started'])*1000,2))
        except PermissionError:
            return self.result(p['trace'],'pin_required','Fresh PIN verification and exact action confirmation are required.',request_id=rid)
        except Exception:
            self.audit.record(p['trace'],p['customer'],'execution_error',error_category='tool_or_retrieval_failure')
            result = self.result(p['trace'],'data_unavailable','Banking data or verification is unavailable. No successful action is being claimed. Contact bank support if an action was interrupted.')
        p['done']=True; p['grant']=None; p['query']=''
        return self.save(p['token'],p['cid'],result)

def money(value):
    from decimal import Decimal
    return f'INR {Decimal(value)/100:,.2f}'

def compose(trace, results, chunks):
    """Deterministic composer: model prose cannot introduce unsupported financial claims."""
    lines=[]; kind='retrieved_fact'; action='none'; alerts=[]
    for entry in results:
        tool,r = entry['tool'],entry['result']
        if r['status']=='not_found':
            lines.append(f'{tool}: No matching records were found in your authorized data.'); kind='not_found'
        elif r['status']=='consent_required':
            lines.append('Personalized offers require your recorded consent.'); kind='clarification_needed'
        elif r['status'] in ('blocked','opened'):
            lines.append(f"{tool}: {r['status']}. Reference: {r.get('card_id',r.get('dispute_id'))}."); kind='action_completed'; action=r['status']
        else:
            for row in r['data']:
                if tool == 'fraud_verification':
                    status = row.get('status', 'unknown')
                    risk = row.get('risk_level', 'unknown')
                    if status == 'confirmed_fraud' or (risk == 'high' and status != 'cleared'):
                        alert = {
                            'severity': 'critical' if status == 'confirmed_fraud' else 'warning',
                            'transaction_id': row.get('transaction_id', row.get('id', 'unknown')),
                            'risk_level': risk,
                            'status': status,
                            'message': ('Confirmed fraud is recorded for this transaction. Contact bank support immediately.'
                                        if status == 'confirmed_fraud' else
                                        'A high-risk transaction is under review. Contact bank support if you do not recognize it.'),
                        }
                        alerts.append(alert)
                parts=[]
                for key,value in row.items():
                    label='account number (masked)' if key == 'account_number' else key.replace('_paise','').replace('_',' ')
                    if key.endswith('_paise') and type(value) is int:
                        value=money(value)
                    elif key=='categories_paise':
                        value=', '.join(f'{k}: {money(v)}' for k,v in value.items())
                    elif key=='last4':
                        value='****'+value
                    parts.append(f'{label}: {value}')
                lines.append('; '.join(parts))
            if tool in ('analyze_expenses','calculate_remaining_funds'):
                kind='calculated'
    if chunks:
        lines.append('Fictional SecureBank demo policy:')
        for c in chunks:
            lines.append(f"{c['text']} [{c['chunk_id']}]")
    if not lines:
        lines=['No adequate approved policy evidence was found. Please contact bank support.']; kind='not_found'
    return dict(answer='\n\n'.join(lines),answer_type=kind,citations=generate_citations(chunks),tools_used=[r['tool'] for r in results],trace_id=trace,action_status=action,evidence=results,alerts=alerts)
