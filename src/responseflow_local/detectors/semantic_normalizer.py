from .semantic_models import SemanticResult


class UnknownEvidenceError(ValueError):
    pass


def unique_preserving_order(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def validate_and_normalize(
    result: SemanticResult,
    available_message_ids: set[str],
) -> SemanticResult:
    evidence = unique_preserving_order(result.evidence_message_ids)

    if not evidence:
        raise UnknownEvidenceError(
            "Анализатор не указал ни одного основания"
        )

    missing = [
        item for item in evidence
        if item not in available_message_ids
    ]

    if missing:
        raise UnknownEvidenceError(
            f"В окне нет оснований: {missing}"
        )

    return result.model_copy(
        update={"evidence_message_ids": evidence}
    )