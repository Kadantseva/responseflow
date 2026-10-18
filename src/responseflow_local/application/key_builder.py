from hashlib import sha256


def _normalize(value: str) -> str:
    return value.strip().lower()


def build_deduplication_key(workspace_id: str, conversation_id: str,
                            finding_type: str, subject_key: str) -> str:
    source = "|".join(map(_normalize, (
        workspace_id, conversation_id, finding_type, subject_key
    )))
    return sha256(source.encode("utf-8")).hexdigest()