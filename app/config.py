from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

@dataclass
class Settings:
    mode: str = os.getenv('APP_MODE', 'development')
    repository: str = os.getenv('REPOSITORY', 'mock')
    database_path: str = os.getenv('DATABASE_PATH', '')
    demo_pin_hash: str = os.getenv('DEMO_PIN_HASH', '')
    router_mode: str = os.getenv('ROUTER_MODE', 'deterministic')
    openrouter_api_key: str = os.getenv('OPENROUTER_API_KEY', '')
    openrouter_model: str = os.getenv('OPENROUTER_MODEL', 'nvidia/nemotron-3.5-lightning:free')
    openrouter_base_url: str = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    embedding_mode: str = os.getenv('EMBEDDING_MODE', 'local_tfidf')
    embedding_model: str = os.getenv('EMBEDDING_MODEL', '')
    rag_index_dir: str = os.getenv('RAG_INDEX_DIR', 'runtime/faiss')
    pin_hash: str = os.getenv('DEMO_PIN_HASH', '')
    session_ttl: int = int(os.getenv('SESSION_TTL_SECONDS', '3600'))
    request_ttl: int = int(os.getenv('REQUEST_TTL_SECONDS', '300'))
    grant_ttl: int = int(os.getenv('GRANT_TTL_SECONDS', '60'))
    pin_max_failures: int = int(os.getenv('PIN_MAX_FAILURES', '5'))
    pin_lock_seconds: int = int(os.getenv('PIN_LOCK_SECONDS', '300'))
