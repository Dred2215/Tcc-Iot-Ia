import os

import redis


def _build_redis_client() -> redis.Redis:
    host = os.getenv("REDIS_HOST")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD") or None
    db = int(os.getenv("REDIS_DB", "0"))

    if not host:
        raise RuntimeError(
            "Configuracao de Redis ausente: defina REDIS_HOST (e REDIS_PORT/REDIS_PASSWORD/REDIS_DB se necessario) no backend/.env."
        )

    return redis.Redis(
        host=host, port=port, password=password, db=db, socket_connect_timeout=5, decode_responses=True
    )


def get_redis_client() -> redis.Redis:
    return _build_redis_client()


def test_connection() -> bool:
    """Testa a conexao com o Redis proprio do backend usando PING."""
    client = _build_redis_client()
    return client.ping()


if __name__ == "__main__":
    try:
        ok = test_connection()
        print(f"[REDIS] Conexao OK: PING -> {ok}")
    except Exception as e:
        print(f"[REDIS] Falha na conexao: {e}")
