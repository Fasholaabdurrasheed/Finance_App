from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType

DEFAULT_CATEGORIES = {
    TransactionType.INCOME: ["Salary", "Freelance", "Investments", "Gift"],
    TransactionType.EXPENSE: ["Food", "Transport", "Rent", "Utilities", "Health", "Entertainment"],
}


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: int) -> list[Category]:
        return (
            self.db.query(Category)
            .filter((Category.owner_id == user_id) | (Category.owner_id.is_(None)))
            .order_by(Category.type.asc(), Category.name.asc())
            .all()
        )

    def create(self, user_id: int, name: str, category_type: TransactionType) -> Category:
        exists = (
            self.db.query(Category)
            .filter(Category.owner_id == user_id, Category.name == name, Category.type == category_type)
            .first()
        )
        if exists:
            raise ValueError("Category already exists")

        category = Category(owner_id=user_id, name=name, type=category_type)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def ensure_default_categories(self, user_id: int) -> None:
        existing = self.db.query(Category).filter(Category.owner_id == user_id).all()
        if existing:
            return

        for category_type, names in DEFAULT_CATEGORIES.items():
            for name in names:
                self.db.add(Category(owner_id=user_id, name=name, type=category_type))

        self.db.commit()
