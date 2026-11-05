def chunks(text: str, *, size: int = 900, overlap: int = 120) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    result: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        result.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return result


_SERVICE_EXPORTS = {
    "DocumentIntake",
    "IntakeResult",
    "ServiceClients",
    "clients",
    "ingest_document",
    "lifespan",
    "parsed_text",
    "service",
    "stable_key",
}


def __getattr__(name: str):
    """Load the web service only when a service symbol is requested."""
    if name not in _SERVICE_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from . import _health_document_app

    try:
        return getattr(_health_document_app, name)
    except AttributeError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error
