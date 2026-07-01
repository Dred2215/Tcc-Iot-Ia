import bcrypt
from sqlalchemy.orm import Session

from ..db.models.user import User
from ..db.repositories import user_repository


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def register_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    phone: str | None = None,
    user_type: str = "client",
) -> User:
    if user_repository.get_by_email(db, email):
        raise EmailAlreadyRegisteredError(f"Email ja cadastrado: {email}")

    password_hash = hash_password(password)
    return user_repository.create(
        db,
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        phone=phone,
        user_type=user_type,
    )


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    """Valida email + senha contra o Postgres. Lanca InvalidCredentialsError se nao bater."""
    user = user_repository.get_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Email ou senha invalidos")

    return user
