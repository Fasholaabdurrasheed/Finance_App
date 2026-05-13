from typing import Generic, TypeVar
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseService(Generic[T]):
    def __init__(self, db: Session):
        self.db = db

    # placeholder for common CRUD helpers
    def list(self):
        raise NotImplementedError()

    def get(self, id: int):
        raise NotImplementedError()

    def create(self, obj_in):
        raise NotImplementedError()

    def update(self, id: int, obj_in):
        raise NotImplementedError()

    def delete(self, id: int):
        raise NotImplementedError()
