import re
from typing import Any

HOOK_TERMS = {
    "segredo", "incrível", "nunca", "sempre", "erro", "verdade", "surpreendente",
    "importante", "atenção", "resultado", "ninguém", "melhor", "pior", "descobri",
    "funciona", "impossível", "rápido", "dinheiro", "problema", "solução",
}
EMPHASIS_TERMS = {"muito", "realmente", "absurdo", "totalmente", "literalmente", "jamais", "exatamente"}


def _score_text(text: str, duration: float) -> tuple[float, list[str]]:
    normalized = text.lower()
    words = re.findall(r"\w+", normalized, flags=re.UNICODE)
    if not words:
        return 0.0, []

    reasons: list[str] = []
    score = 0.25
    hooks = sorted({word for word in words if word in HOOK_TERMS})
    emphasis = sorted({word for word in words if word in EMPHASIS_TERMS})

    if "?" in text:
        score += 0.18
        reasons.append("Pergunta que pode despertar curiosidade")
    if "!" in text:
        score += 0.08
        reasons.append("Fala com ênfase")
    if hooks:
        score += min(0.25, 0.08 * len(hooks))
        reasons.append("Termos de impacto: " + ", ".join(hooks[:4]))
    if emphasis:
        score += 0.08
        reasons.append("Linguagem enfática")
    if 8 <= len(words) <= 45:
        score += 0.12
        reasons.append("Trecho com tamanho adequado para uma ideia")
    elif len(words) > 70:
        score -= 0.08
    if 4 <= duration <= 18:
        score += 0.08
    return max(0.0, min(1.0, score)), reasons


def suggest_clips(
    segments: list[dict[str, Any]],
    min_duration: float = 15.0,
    max_duration: float = 60.0,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Create explainable candidate clips from timestamped speech segments."""
    valid = [
        item for item in segments
        if isinstance(item.get("start"), (int, float))
        and isinstance(item.get("end"), (int, float))
        and item["end"] > item["start"]
        and isinstance(item.get("text"), str)
        and item["text"].strip()
    ]
    valid.sort(key=lambda item: float(item["start"]))
    if not valid:
        return []

    candidates: list[dict[str, Any]] = []
    for start_index, first in enumerate(valid):
        collected: list[dict[str, Any]] = []
        start = float(first["start"])
        end = start
        for segment in valid[start_index:]:
            segment_start = float(segment["start"])
            segment_end = float(segment["end"])
            if collected and segment_start - end > 2.5:
                break
            if segment_end - start > max_duration:
                break
            collected.append(segment)
            end = max(end, segment_end)
            duration = end - start
            if duration < min_duration:
                continue

            text = " ".join(item["text"].strip() for item in collected)
            segment_scores = [
                _score_text(item["text"], float(item["end"]) - float(item["start"]))
                for item in collected
            ]
            base = sum(item[0] for item in segment_scores) / len(segment_scores)
            coverage = min(1.0, len(collected) / 4)
            score = round(min(1.0, base * 0.8 + coverage * 0.2), 3)
            reasons = list(dict.fromkeys(
                reason for _, why in segment_scores for reason in why
            ))[:4]
            candidates.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
                "score": score,
                "text": text,
                "reasons": reasons or ["Trecho contínuo de fala"],
            })
            break

    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        overlaps = any(
            candidate["start"] < chosen["end"] and candidate["end"] > chosen["start"]
            for chosen in selected
        )
        if not overlaps:
            selected.append(candidate)
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda item: item["start"])
