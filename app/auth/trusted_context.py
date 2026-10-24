from dataclasses import dataclass, field
import secrets
import time

@dataclass
class Session:
    customer: str
    expires: float
    conversations: dict = field(default_factory=dict)

class SessionStore:
    """Opaque bearer credentials issued only via trusted upstream integration or local fixture."""
    def __init__(self, settings, customer_ids=None):
        self.settings = settings
        self.sessions = {}
        self.customer_ids = set(customer_ids or [f'C{n}' for n in range(1001, 1011)])

    def issue_development(self, customer, peer):
        if self.settings.mode != 'development' or peer not in ('127.0.0.1', '::1', 'testclient'):
            raise PermissionError('Development identity is local-only')
        if customer not in self.customer_ids:
            raise PermissionError('Unknown demo identity')
        token = secrets.token_urlsafe(32)
        self.sessions[token] = Session(customer, time.time()+self.settings.session_ttl)
        return token

    def get(self, token):
        session = self.sessions.get(token)
        if not session or session.expires <= time.time():
            self.sessions.pop(token, None)
            raise PermissionError('Trusted session is missing or expired')
        return session
