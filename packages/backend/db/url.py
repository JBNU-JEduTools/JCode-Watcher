def normalize_database_url(url: str) -> str:
    """Accept the standard URI emitted by CloudNativePG app Secrets."""
    if url.startswith("postgresql+psycopg://") or url.startswith("sqlite:"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    raise RuntimeError(
        "DB_URL은 postgresql://, postgresql+psycopg:// 또는 "
        "테스트용 sqlite:// 형식이어야 합니다."
    )
