import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _build_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL")

    # DATABASE_URL no .env atual usa o prefixo "jdbc:postgresql://", que nao e
    # um DSN valido para o SQLAlchemy/psycopg2. Nesse caso, montamos a URL via DB_*.
    if raw_url and not raw_url.startswith("jdbc:"):
        return raw_url

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([host, port, name, user, password]):
        raise RuntimeError(
            "Configuracao de banco ausente: defina DATABASE_URL (formato postgresql://) "
            "ou DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD."
        )

    return f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
