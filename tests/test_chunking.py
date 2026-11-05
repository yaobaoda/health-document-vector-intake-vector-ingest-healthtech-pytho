from health_intake.health_document_service import chunks


def test_chunk_overlap_preserves_boundary_context() -> None:
    text = "abcdefghij"

    assert chunks(text, size=6, overlap=2) == ["abcdef", "efghij"]
