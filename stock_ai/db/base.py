from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all ORM models. models/ should import and inherit from this class.
    This will be used by alembic for migrations as well.
    """
    pass