import os
from functools import lru_cache
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
from tuya_connector import TuyaOpenAPI

# 🔐 Carrega .env local para cenários de execução direta
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# 🔐 Credenciais via variáveis de ambiente para evitar segredos no código
ACCESS_ID = os.getenv("TUYA_ACCESS_ID")
ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET")
ENDPOINT = os.getenv("TUYA_ENDPOINT", "https://openapi.tuyaus.com")

# Identificadores específicos do ambiente
UID = os.getenv("TUYA_UID")
HOME_ID = os.getenv("TUYA_HOME_ID")


def _require(value: Optional[str], env_var: str) -> str:
    """Valida e retorna o valor de uma variável de ambiente obrigatória."""
    if not value:
        raise RuntimeError(f"Defina a variável de ambiente {env_var} antes de usar a API Tuya.")
    return value


def _connect() -> TuyaOpenAPI:
    """Cria e autentica o cliente Tuya apenas quando necessário."""
    access_id = _require(ACCESS_ID, "TUYA_ACCESS_ID")
    access_secret = _require(ACCESS_SECRET, "TUYA_ACCESS_SECRET")

    api = TuyaOpenAPI(ENDPOINT, access_id, access_secret)
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
    return _require(HOME_ID, "TUYA_HOME_ID")


def get_uid() -> Optional[str]:
    """UID pode ser opcional dependendo do fluxo de autenticação."""
    return UID
