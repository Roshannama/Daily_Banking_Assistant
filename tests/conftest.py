import secrets
import pytest
from argon2 import PasswordHasher
from app.config import Settings
from app.data.mock_repository import MockBankingRepository
from app.service import BankingService
from app.rag.retrieval import Retriever

class Secret(str):
    def __repr__(self): return '<redacted test credential>'

@pytest.fixture(scope='session')
def credential():
    return Secret(''.join(str(secrets.randbelow(10)) for _ in range(8)))

@pytest.fixture(scope='session')
def encoded(credential):
    return PasswordHasher().hash(credential)

@pytest.fixture(scope='session')
def retriever():
    return Retriever()

@pytest.fixture
def service(tmp_path,encoded,retriever):
    config=Settings(router_mode='deterministic',pin_hash=encoded)
    return BankingService(config,MockBankingRepository(encoded),retriever,tmp_path/'audit.jsonl')

@pytest.fixture
def session(service):
    token=service.sessions.issue_development('C1001','testclient')
    return token,service.conversation(token)
