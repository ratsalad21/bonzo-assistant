import os
from functools import lru_cache

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_BASE_URL


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Create and cache one OpenAI client for the current process.

    Reusing the client avoids rebuilding configuration on every call and gives
    the rest of the app one shared place to obtain the API client.
    """
    # If the .env file defines OPENAI_BASE_URL as an empty string, remove it from
    # the process environment so the SDK falls back to its real default endpoint.
    if not OPENAI_BASE_URL:
        os.environ.pop("OPENAI_BASE_URL", None)

    kwargs: dict[str, str] = {}
    if OPENAI_API_KEY:
        kwargs["api_key"] = OPENAI_API_KEY
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    return OpenAI(**kwargs)
