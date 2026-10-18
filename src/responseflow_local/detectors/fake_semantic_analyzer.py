import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from .semantic_models import SemanticResult
from responseflow_local.domain.models import ConversationWindow


class FixtureEntry(BaseModel):
    workspace_id: str
    conversation_id: str
    window_checksum: str
    items: tuple[SemanticResult, ...]


class FakeSemanticAnalyzer:
    def __init__(self, fixture_path: Path) -> None:
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
        entries = TypeAdapter(tuple[FixtureEntry, ...]).validate_python(raw["results"])
        self._items = {
            (entry.workspace_id, entry.conversation_id): entry.items
            for entry in entries
        }
        if len(self._items) != len(entries):
            raise ValueError("В заглушке повторяется рабочая область и беседа")

    def analyze(self, window: ConversationWindow) -> tuple[SemanticResult, ...]:
        return tuple(self._items.get(
            (window.workspace_id, window.conversation_id), ()
        ))