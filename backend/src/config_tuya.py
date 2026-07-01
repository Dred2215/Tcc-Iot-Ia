import os
from functools import lru_cache
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
from tuya_connector import TuyaOpenAPI

# Carrega backend/.env para cenários de execução direta deste módulo
# (ex: rodar `python -m src.config_tuya` isoladamente). Quando importado
# via api.py, o .env já foi carregado antes por lá; load_dotenv aqui é
# idempotente e não sobrescreve valores já presentes em os.environ.
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR / ".env")


def _require(value: Optional[str], env_var: str) -> str:
    """Valida e retorna o valor de uma variável de ambiente obrigatória."""
    if not value:
        raise RuntimeError(f"Defina a variável de ambiente {env_var} antes de usar a API Tuya.")
    return value


def _connect() -> TuyaOpenAPI:
    """Cria e autentica o cliente Tuya apenas quando necessário."""
    # Lidas em tempo de chamada (não no import do módulo) para não depender
    # da ordem de import em relação ao load_dotenv de quem importa este módulo.
    access_id = _require(os.getenv("TUYA_ACCESS_ID"), "TUYA_ACCESS_ID")
    access_secret = _require(os.getenv("TUYA_ACCESS_SECRET"), "TUYA_ACCESS_SECRET")
    endpoint = os.getenv("TUYA_ENDPOINT", "https://openapi.tuyaus.com")

    api = TuyaOpenAPI(endpoint, access_id, access_secret)
    api.connect()
    return api


@lru_cache(maxsize=1)
def get_openapi() -> TuyaOpenAPI:
    """
    Retorna instância singleton do cliente Tuya.
    A conexão só é aberta na primeira chamada.
    """
    return _connect()


def get_home_id() -> str:
    return _require(os.getenv("TUYA_HOME_ID"), "TUYA_HOME_ID")


def get_uid() -> Optional[str]:
    """UID pode ser opcional dependendo do fluxo de autenticação."""
    return os.getenv("TUYA_UID")
