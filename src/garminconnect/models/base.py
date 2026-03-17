from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase, MappedAsDataclass):
    """Base class for all models. Uses mapped_as_dataclass for clean init."""
    pass
