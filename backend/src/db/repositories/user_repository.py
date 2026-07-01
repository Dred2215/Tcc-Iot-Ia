from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.user import User


def get_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def create(
    db: Session,
    *,
    full_name: str,
    email: str,
    password_hash: str,
    phone: str | None = None,
    user_type: str = "client",
) -> User:
    user = User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        phone=phone,
        type=user_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
