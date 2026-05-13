from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime, func

Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class IDMixin:
    id = Column(Integer, primary_key=True, index=True)


# Example BaseModel to inherit from
class BaseModel(Base, IDMixin, TimestampMixin):
    __abstract__ = True
