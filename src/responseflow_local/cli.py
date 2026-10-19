
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
import json

import typer

from responseflow_local.container import (
    ApplicationContainer,
    build_application,
)
from responseflow_local.application.review import (
    AcknowledgeRequest,
    RejectRequest,
    ResolveRequest,
    SnoozeRequest,
)

app = typer.Typer(
    help="ResponseFlow Local — анализ клиентских переписок",
    no_args_is_help=True,
)


def container(
    database: Path,
    fixture_root: Path = Path("data/fixtures"),
) -> ApplicationContainer:
    """Создать контейнер приложения."""
    return build_application(database, fixture_root)


@app.command("init-db")
def init_db(
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
        help="Путь к SQLite-базе",
    ),
) -> None:
    """Создать базу данных или обновить её схему."""
    container(database)
    typer.echo(f"База данных инициализирована: {database}")



@app.command("import-messages")
def import_messages(
    file: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        dir_okay=False,
        help="Путь к JSONL-файлу с сообщениями",
    ),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
        help="Путь к SQLite-базе",
    ),
    fixtures: Path = typer.Option(
        Path("data/fixtures"),
        "--fixtures",
        help="Каталог с participants.json и projects.json",
    ),
) -> None:
    """Импортировать сообщения из JSONL."""
    application = container(database, fixtures)

    records = []
    try:
        with file.open("r", encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue

                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise typer.BadParameter(
                        f"Некорректный JSON в строке {line_number}: {error}"
                    ) from error

        imported = application.import_service.import_records(records)

    except (ValueError, OSError) as error:
        typer.echo(f"Ошибка импорта: {error}", err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Источник сообщений: {file}")
    typer.echo(f"Импортировано сообщений: {imported}")



@app.command("analyze")
def analyze(
    workspace: str = typer.Option(
        ...,
        "--workspace",
        "-w",
        help="Идентификатор рабочей области",
    ),
    analysis_time: str = typer.Option(
        ...,
        "--analysis-time",
        help="Время анализа в ISO 8601 с часовым поясом",
    ),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
        help="Путь к SQLite-базе",
    ),
) -> None:
    """Запустить анализ переписок."""
    try:
        analysis_time = datetime.fromisoformat(
            analysis_time.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise typer.BadParameter(
            "Используйте ISO 8601, например "
            "2026-10-17T12:00:00+00:00"
        ) from error

    if analysis_time.tzinfo is None or analysis_time.utcoffset() is None:
        raise typer.BadParameter(
            "Укажите часовой пояс, например 2026-10-17T12:00:00+00:00"
        )

    application = container(database)
    report = application.analysis_service.run(
        workspace,
        analysis_time,
    )
    typer.echo(report.model_dump_json(indent=2))


@app.command("list-findings")
def list_findings(
    workspace: str = typer.Option(
        ...,
        "--workspace",
        "-w",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
    ),
    priority: str | None = typer.Option(
        None,
        "--priority",
    ),
    project_id: str | None = typer.Option(
        None,
        "--project",
    ),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
    ),
) -> None:
    """Вывести карточки для рабочей области."""
    application = container(database)

    findings = application.inbox_service.list_findings(
        workspace,
        status=status,
        priority=priority,
        project_id=project_id,
    )

    for finding in findings:
        typer.echo(
            f"{finding.finding_id} | "
            f"{finding.status} | "
            f"{finding.type} | "
            f"{finding.summary} | "
            f"версия={finding.version}"
        )

    typer.echo(f"Всего карточек: {len(findings)}")


@app.command("show-finding")
def show_finding(
    finding_id: UUID = typer.Argument(
        ...,
        help="UUID карточки",
    ),
    workspace: str = typer.Option(
        ...,
        "--workspace",
        "-w",
    ),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
    ),
) -> None:
    """Показать карточку, основания и историю решений."""
    application = container(database)
    service = application.inbox_service

    finding = service.get_finding(workspace, finding_id)
    evidence = service._repository.list_evidence(finding_id)
    history = service.get_history(workspace, finding_id)

    typer.echo(finding.model_dump_json(indent=2))

    typer.echo("\nОснования:")
    for item in evidence:
        typer.echo(
            f"- {item.message_external_id} ({item.added_at})"
        )

    typer.echo("\nИстория решений:")
    for event in history:
        typer.echo(
            f"- {event.occurred_at} | "
            f"{event.event_type} | {event.details}"
        )


@app.command("acknowledge")
def acknowledge(
    finding_id: UUID = typer.Argument(...),
    workspace: str = typer.Option(..., "--workspace", "-w"),
    author: str = typer.Option(..., "--author"),
    version: int = typer.Option(..., "--version", min=1),
    comment: str = typer.Option(
        "Принято в работу",
        "--comment",
    ),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
    ),
) -> None:
    """Принять карточку в работу."""
    command = AcknowledgeRequest(
        author=author,
        expected_version=version,
        occurred_at=datetime.now(timezone.utc),
        comment=comment,
    )

    result = container(database).inbox_service.acknowledge(
        workspace,
        finding_id,
        command,
    )
    typer.echo(result.model_dump_json(indent=2))


@app.command("snooze")
def snooze(
    finding_id: UUID = typer.Argument(...),
    workspace: str = typer.Option(..., "--workspace", "-w"),
    author: str = typer.Option(..., "--author"),
    version: int = typer.Option(..., "--version", min=1),
    until: str = typer.Option(
        ...,
        "--until",
        help="Дата окончания snooze в ISO 8601 с часовым поясом",
    ),
    reason: str = typer.Option(..., "--reason"),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
    ),
) -> None:
    """Отложить карточку до указанного времени."""
    try:
        until = datetime.fromisoformat(until.replace("Z", "+00:00"))
    except ValueError as error:
        raise typer.BadParameter(
            "Укажите дату в формате ISO 8601, "
            "например 2026-10-20T10:00:00+03:00"
        ) from error

    if until.tzinfo is None or until.utcoffset() is None:
        raise typer.BadParameter(
            "Укажите часовой пояс в --until, например +03:00"
        )

    command = SnoozeRequest(
        author=author,
        expected_version=version,
        occurred_at=datetime.now(timezone.utc),
        until=until,
        reason=reason,
    )

    result = container(database).inbox_service.snooze(
        workspace,
        finding_id,
        command,
    )
    typer.echo(result.model_dump_json(indent=2))


@app.command("resolve")
def resolve(
    finding_id: UUID = typer.Argument(...),
    workspace: str = typer.Option(..., "--workspace", "-w"),
    author: str = typer.Option(..., "--author"),
    version: int = typer.Option(..., "--version", min=1),
    comment: str = typer.Option(..., "--comment"),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
    ),
) -> None:
    """Закрыть карточку как решённую."""
    command = ResolveRequest(
        author=author,
        expected_version=version,
        occurred_at=datetime.now(timezone.utc),
        comment=comment,
    )

    result = container(database).inbox_service.resolve(
        workspace,
        finding_id,
        command,
    )
    typer.echo(result.model_dump_json(indent=2))


@app.command("reject")
def reject(
    finding_id: UUID = typer.Argument(...),
    workspace: str = typer.Option(..., "--workspace", "-w"),
    author: str = typer.Option(..., "--author"),
    version: int = typer.Option(..., "--version", min=1),
    reason_code: str = typer.Option(
        ...,
        "--reason-code",
        help=(
            "not_actionable, wrong_type, already_resolved "
            "или insufficient_evidence"
        ),
    ),
    comment: str = typer.Option(..., "--comment"),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
    ),
) -> None:
    """Отклонить карточку с указанием причины."""
    try:
        command = RejectRequest(
            author=author,
            expected_version=version,
            occurred_at=datetime.now(timezone.utc),
            reason_code=reason_code,
            comment=comment,
        )
    except (ValueError, TypeError) as error:
        raise typer.BadParameter(str(error)) from error

    result = container(database).inbox_service.reject(
        workspace,
        finding_id,
        command,
    )
    typer.echo(result.model_dump_json(indent=2))


@app.command("report")
def report(
    workspace: str = typer.Option(
        ...,
        "--workspace",
        "-w",
    ),
    database: Path = typer.Option(
        Path("data/responseflow.db"),
        "--database",
        "-d",
    ),
) -> None:
    """Показать сводный отчёт по рабочей области."""
    result = container(database).report_service.build(workspace)

    if hasattr(result, "model_dump_json"):
        typer.echo(result.model_dump_json(indent=2))
    else:
        typer.echo(str(result))


if __name__ == "__main__":
    app()
