from hashlib import sha256


def hash_password(raw: str) -> str:
  return sha256(raw.encode("utf-8")).hexdigest()


def verify_password(raw: str, hashed: str) -> bool:
  return hash_password(raw) == hashed


