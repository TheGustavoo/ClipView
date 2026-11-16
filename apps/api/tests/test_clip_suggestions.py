from app.services.clip_suggestions import suggest_clips


def test_suggest_clips_returns_ranked_non_overlapping_candidates() -> None:
    segments = [
        {"start": 0, "end": 5, "text": "Hoje vou explicar uma coisa muito importante."},
        {"start": 5, "end": 10, "text": "Você conhece o segredo para resolver esse problema?"},
        {"start": 10, "end": 16, "text": "Essa é a verdade que ninguém conta!"},
        {"start": 70, "end": 76, "text": "Primeiro ponto de uma nova explicação."},
        {"start": 76, "end": 83, "text": "Esse resultado é realmente surpreendente!"},
        {"start": 83, "end": 90, "text": "Agora você sabe como funciona."},
    ]

    suggestions = suggest_clips(segments, min_duration=15, max_duration=40)

    assert len(suggestions) >= 1
    assert all(item["end"] > item["start"] for item in suggestions)
    assert all(item["score"] >= 0 and item["score"] <= 1 for item in suggestions)
    assert all("reasons" in item and item["reasons"] for item in suggestions)
    for previous, current in zip(suggestions, suggestions[1:]):
        assert previous["end"] <= current["start"]


def test_suggest_clips_ignores_invalid_segments() -> None:
    assert suggest_clips([
        {"start": 4, "end": 2, "text": "Horário inválido"},
        {"start": 0, "end": 3, "text": ""},
        {"start": "zero", "end": 4, "text": "Tipo inválido"},
    ]) == []


def test_suggest_clips_returns_empty_when_speech_is_too_short() -> None:
    assert suggest_clips([
        {"start": 0, "end": 4, "text": "Uma frase curta."},
    ]) == []
