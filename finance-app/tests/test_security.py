from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.core.config import settings


def test_password_hash_and_verify() -> None:
    password = "StrongPass123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)


def test_create_and_decode_access_token() -> None:
    settings.JWT_SECRET_KEY = "test-secret-key-with-at-least-thirty-two-characters"
    token = create_access_token("1", expires_minutes=5)
    payload = decode_access_token(token)

    assert payload["sub"] == "1"
