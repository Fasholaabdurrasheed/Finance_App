from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


# Extended aliases for better column detection
# Handles common variations across different finance software
DATE_ALIASES = {
    "date", "transaction_date", "transaction date", "txn date", 
    "posted date", "value date", "booking date", "entry date",
    "trans_date", "transaction_datetime", "posting_date", "trans date"
}
AMOUNT_ALIASES = {
    "amount", "transaction amount", "value", "total", "net amount",
    "transaction_amount", "txn amount", "amt", "sum", "net"
}
DEBIT_ALIASES = {
    "debit", "debits", "outflow", "expense", "expenses",
    "withdrawal", "payment", "debit amount", "out", "dr"
}
CREDIT_ALIASES = {
    "credit", "credits", "inflow", "income", "receipts",
    "deposit", "inflow amount", "in", "cr"
}
TYPE_ALIASES = {
    "type", "transaction type", "direction", "trans type", 
    "transaction_type", "txn_type", "trx_type", "kind", "category_type"
}
DESCRIPTION_ALIASES = {
    "description", "details", "memo", "note", "notes", "reference",
    "narration", "particulars", "remarks", "desc", "detail", "narrative"
}
CATEGORY_ALIASES = {
    "category", "category name", "subcategory", "tag", "merchant", "group",
    "category_name", "merchant name", "vendor", "party", "account"
}


@dataclass(slots=True)
class NormalizedColumnSet:
    date: str | None = None
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    transaction_type: str | None = None
    description: str | None = None
    category: str | None = None


def normalize_column_name(column_name: str) -> str:
    return " ".join(column_name.strip().lower().replace("_", " ").split())


def resolve_columns(columns: list[str]) -> NormalizedColumnSet:
    normalized_map = {normalize_column_name(column): column for column in columns}

    def find(alias_set: set[str]) -> str | None:
        for alias in alias_set:
            if alias in normalized_map:
                return normalized_map[alias]
        return None

    return NormalizedColumnSet(
        date=find(DATE_ALIASES),
        amount=find(AMOUNT_ALIASES),
        debit=find(DEBIT_ALIASES),
        credit=find(CREDIT_ALIASES),
        transaction_type=find(TYPE_ALIASES),
        description=find(DESCRIPTION_ALIASES),
        category=find(CATEGORY_ALIASES),
    )


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    text = str(value).strip()
    return text or None


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_transaction_type(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None

    lowered = text.lower()
    if lowered in {"income", "credit", "in", "inflow", "deposit", "earning", "earnings"}:
        return "income"
    if lowered in {"expense", "debit", "out", "outflow", "withdrawal", "payment", "spend", "spending"}:
        return "expense"
    return None


def infer_transaction_type_from_amount(amount: Decimal) -> str:
    return "income" if amount >= 0 else "expense"


def normalize_amount(amount: Decimal) -> Decimal:
    return abs(amount).quantize(Decimal("0.01"))


def row_signature(transaction_date: Any, amount: Decimal, transaction_type: str, description: str | None, category: str | None) -> tuple[Any, ...]:
    return (
        transaction_date,
        amount,
        transaction_type,
        (description or "").strip().lower(),
        (category or "").strip().lower(),
    )