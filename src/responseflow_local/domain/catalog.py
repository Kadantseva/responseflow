import json
from pathlib import Path
from typing import Dict, Tuple, TypeVar

from pydantic import BaseModel, TypeAdapter

from .models import Participant, Project

T = TypeVar("T", bound=BaseModel)


def load_list(path: Path, model_type: type[T]) -> tuple[T, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TypeAdapter(tuple[model_type, ...]).validate_python(raw)


class Catalog:
    def __init__(self, participants: tuple[Participant, ...],
                 projects: tuple[Project, ...]) -> None:
        self._participants_index: Dict[Tuple[str, str], Participant] = {}
        self._projects_index: Dict[Tuple[str, str], Project] = {}
        for p in participants:
            key = (p.workspace_id, p.participant_id)
            if key in self._participants_index:
                existing = self._participants_index[key]
                raise ValueError(
                    f"Дубликат участника: workspace_id={p.workspace_id}, "
                    f"participant_id={p.participant_id}. "
                    f"Уже есть запись с revision={existing.revision}"
                )
            self._participants_index[key] = p

        for proj in projects:
            key = (proj.workspace_id, proj.conversation_id)
            if key in self._projects_index:
                existing = self._projects_index[key]
                raise ValueError(
                    f"Дубликат проекта для разговора: workspace_id={proj.workspace_id}, "
                    f"conversation_id={proj.conversation_id}. "
                    f"Уже есть проект с id={existing.project_id}"
                )
            self._projects_index[key] = proj

    def participant(self, workspace_id: str, participant_id: str) -> Participant:
        key = (workspace_id, participant_id)
        result = self._participants_index.get(key)
        if result is None:
            raise KeyError(
                f"Участник не найден: workspace_id={workspace_id}, participant_id={participant_id}"
            )
        return result

    def project_for_conversation(self, workspace_id: str,
                                 conversation_id: str) -> Project:
        key = (workspace_id, conversation_id)
        result = self._projects_index.get(key)
        if result is None:
            raise KeyError(
                f"Проект не найден для разговора: workspace_id={workspace_id}, conversation_id={conversation_id}"
            )
        return result