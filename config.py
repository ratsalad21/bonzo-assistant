"""Central configuration for the app.

This module reads environment variables once, defines shared constants, and
creates the local folders the app expects. Keeping that work in one place makes
the rest of the code simpler because other modules can import ready-to-use
settings instead of repeating the same setup logic.
"""

import os
from pathlib import Path

from dateutil import tz
from dotenv import load_dotenv

# Load local development settings from .env before reading environment variables.
# We use utf-8-sig because some Windows tools save .env with a UTF-8 BOM, which
# can turn the first key into "\ufeffOPENAI_API_KEY" unless the BOM is stripped.
load_dotenv(encoding="utf-8-sig")


def _load_azure_app_configuration_into_env() -> None:
    """Optionally load config values from Azure App Configuration into env vars.

    The app still works fine without Azure. This loader only runs when an
    App Configuration endpoint is provided, which keeps local development easy
    while still letting a hosted deployment centralize its settings.
    """
    endpoint = os.getenv("APP_CONFIGURATION_ENDPOINT", "").strip()
    if not endpoint:
        return

    try:
        from azure.appconfiguration.provider import SettingSelector, load
        from azure.identity import DefaultAzureCredential
    except ImportError:
        # The Azure packages are optional for local work. We only need them when
        # the app is actually pointed at App Configuration.
        return

    label = os.getenv("APP_CONFIGURATION_LABEL", "").strip()
    prefix = os.getenv("APP_CONFIGURATION_PREFIX", "").strip()
    key_filter = f"{prefix}*" if prefix else "*"
    selects = [SettingSelector(key_filter=key_filter, label_filter="\0")]
    if label:
        # Load unlabeled settings first, then let the environment label override
        # them. That gives us simple layered config without adding more logic.
        selects.append(SettingSelector(key_filter=key_filter, label_filter=label))

    credential = DefaultAzureCredential()
    loaded = load(
        endpoint=endpoint,
        credential=credential,
        keyvault_credential=credential,
        selects=selects,
        trim_prefixes=[prefix] if prefix else None,
    )

    for key, value in loaded.items():
        # App Service environment variables should still win if they are already
        # set, so App Configuration behaves like a central default source.
        if key not in os.environ or not os.environ[key]:
            os.environ[key] = str(value)


_load_azure_app_configuration_into_env()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MOCK_MODE = os.getenv("MOCK_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
# This is our local budgeting hint for trimming history before requests go out.
APP_MODEL_CONTEXT_WINDOW = int(os.getenv("APP_MODEL_CONTEXT_WINDOW", "128000"))

# These paths stay local on purpose because local persistence is much easier to
# learn from than a hosted storage system.
DOCS_DIR = Path(os.getenv("DOCS_DIR", "./docs")).resolve()
CHAT_HISTORY_DIR = Path(os.getenv("CHAT_HISTORY_DIR", "./chat_history")).resolve()
CHROMA_DB_PATH = Path(os.getenv("CHROMA_DB_PATH", "./chroma_db")).resolve()

# These constants are small "teaching defaults" rather than deeply optimized
# production settings. They aim to keep the app approachable and stable.
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

# The app shows timestamps in Eastern time because that is the current learning
# context for this project. Keeping the timezone explicit avoids hidden machine
# defaults changing how timestamps appear.
EASTERN = tz.gettz("America/New_York")
