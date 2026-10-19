
from collections.abc import Iterable

from pydantic import ValidationError

from responseflow_local.domain.models import MessageRevision
from responseflow_local.storage.sqlite_message_repository import (
    SqliteMessageRepository,
)


class MessageImportError(ValueError):
    pass


class MessageImportService:
    def __init__(
        self,
        repository: SqliteMessageRepository,
    ) -> None:
        self._repository = repository

    def import_messages(
        self,
        messages: Iterable[MessageRevision],
    ) -> int:
        validated_messages: list[MessageRevision] = []

        for message in messages:
            try:
                validated = MessageRevision.model_validate(
                    message.model_dump()
                )
            except ValidationError as error:
                raise MessageImportError(
                    "Сообщение не прошло валидацию"
                ) from error

            validated_messages.append(validated)

        return self._repository.save_messages(
            tuple(validated_messages)
        )

    def import_records(
        self,
        records: Iterable[dict],
    ) -> int:
        messages: list[MessageRevision] = []

        for record in records:
            try:
                message = MessageRevision.model_validate(record)
            except ValidationError as error:
                raise MessageImportError(
                    "Импортируемая запись не соответствует MessageRevision"
                ) from error

            messages.append(message)

        return self._repository.save_messages(tuple(messages))
