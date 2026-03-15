import os
from pathlib import Path

from dateutil import tz
from dotenv import load_dotenv

# Load local development settings from .env before reading environment variables.
# We use utf-8-sig because some Windows tools save .env with a UTF-8 BOM, which
# can turn the first key into "\ufeffOPENAI_API_KEY" unless the BOM is stripped.
load_dotenv(encoding="utf-8-sig")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MOCK_MODE = os.getenv("MOCK_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
# This is our local budgeting hint for trimming history before requests go out.
APP_MODEL_CONTEXT_WINDOW = int(os.getenv("APP_MODEL_CONTEXT_WINDOW", "128000"))

DOCS_DIR = Path(os.getenv("DOCS_DIR", "./docs")).resolve()
CHAT_HISTORY_DIR = Path(os.getenv("CHAT_HISTORY_DIR", "./chat_history")).resolve()
CHROMA_DB_PATH = Path(os.getenv("CHROMA_DB_PATH", "./chroma_db")).resolve()

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_CONTEXT_CHARS = 2000
MAX_HISTORY_MESSAGES = 8
REQUEST_TIMEOUT = 300
RETRIEVAL_K = 5
DOC_PREVIEW_CHARS = 3000
DOC_SEARCH_RESULTS = 5
MIN_OUTPUT_TOKENS = 64
DEFAULT_OUTPUT_TOKENS = 700
APPROX_CHARS_PER_TOKEN = 4
MAX_SPECIALIST_STEPS = 3
SAMPLE_DOC_NAME = "sample-deploy-note.md"
# RAG starts disabled so the repo teaches the simpler chat loop first.
DEFAULT_USE_RAG = False
DEFAULT_MULTI_AGENT_ROUTING = True
DEFAULT_USE_WRITING_AGENT = True
DEFAULT_USE_CODING_AGENT = True

DOCS_DIR.mkdir(parents=True, exist_ok=True)
CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

EASTERN = tz.gettz("America/New_York")
