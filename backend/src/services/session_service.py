import json
import os
import secrets
from typing import Optional, TypedDict

from ..redis_session import get_redis_client

SESSION_KEY_PREFIX = "session_id:"


class SessionData(TypedDict):
    id: str
    email: str
    full_name: str
    type: str


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def _session_ttl() -> int:
    return int(os.getenv("REDIS_SESSION_TTL", "3600"))


def create_session(*, user_id: str, email: str, full_name: str, user_type: str) -> str:
    """Gera um session_id novo, persiste os dados do usuario no Redis com TTL e retorna o session_id."""
    session_id = secrets.token_urlsafe(32)
    session_data: SessionData = {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "type": user_type,
    }

    client = get_redis_client()
    client.set(_session_key(session_id), json.dumps(session_data), ex=_session_ttl())

    return session_id


def get_session(session_id: str) -> Optional[SessionData]:
    """Recupera os dados da sessao a partir do session_id, ou None se nao existir/expirou."""
    client = get_redis_client()
    raw = client.get(_session_key(session_id))
    if not raw:
        return None

    return json.loads(raw)
