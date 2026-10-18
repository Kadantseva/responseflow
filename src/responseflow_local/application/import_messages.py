from collections.abc import Iterable

from pydantic import ValidationError

from responseflow_local.domain.models import MessageRevision
from responseflow_local.storage.sqlite_message_repository import SqliteMessageRepository


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
        imported = 0

        for message in messages:
            try:
                validated = MessageRevision.model_validate(
                    message.model_dump()
                )
            except ValidationError as error:
                raise MessageImportError(
                    "Сообщение не прошло валидацию"
                ) from error

            self._repository.add(validated)
            imported += 1

        return imported

    def import_records(
        self,
        records: Iterable[dict],
    ) -> int:
        imported = 0

        for record in records:
            try:
                message = MessageRevision.model_validate(record)
            except ValidationError as error:
                raise MessageImportError(
                    "Импортируемая запись не соответствует MessageRevision"
                ) from error

            self._repository.add(message)
            imported += 1

        return imported
