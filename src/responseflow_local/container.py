
from dataclasses import dataclass
import json
from pathlib import Path

from responseflow_local.application.analyze import AnalysisService
from responseflow_local.application.finding_service import FindingService
from responseflow_local.application.import_messages import MessageImportService
from responseflow_local.application.report import ReportService
from responseflow_local.application.review import InboxService

from responseflow_local.domain.window_builder import WindowBuilder
from responseflow_local.domain.catalog import Catalog

from responseflow_local.storage.sqlite import SqliteDatabase
from responseflow_local.storage.sqlite_message_repository import (
    SqliteMessageRepository,
)
from responseflow_local.storage.sqlite_repositories import (
    SqliteFindingRepository,
)
import json
from responseflow_local.domain.models import Participant, Project
from responseflow_local.detectors.unanswered import UnansweredDetector
from responseflow_local.llm.analyzer import LlmSituationAnalyzer
from responseflow_local.llm.settings import load_settings
from responseflow_local.llm.vsellm_provider import VseLlmProvider
from responseflow_local.detectors.llm_situations import LlmSituationDetector

PROMPT_PATH=path = Path("data/fixtures/system-prompt-v1.md")

@dataclass(frozen=True)
class ApplicationContainer:
    import_service: MessageImportService
    analysis_service: AnalysisService
    inbox_service: InboxService
    report_service: ReportService


def build_application(
    database_path: Path,
    fixture_root: Path = Path("data/fixtures"),
) -> ApplicationContainer:
    """Создать и связать компоненты приложения."""

    database = SqliteDatabase(database_path)
    database.initialize()

    message_repository = SqliteMessageRepository(database)
    finding_repository = SqliteFindingRepository(database)

    participants_path = fixture_root / "participants.json"
    projects_path = fixture_root / "projects.json"

    if not participants_path.is_file():
        raise FileNotFoundError(
            f"Не найден файл участников: {participants_path}"
        )

    if not projects_path.is_file():
        raise FileNotFoundError(
            f"Не найден файл проектов: {projects_path}"
        )

    with participants_path.open("r", encoding="utf-8") as file:
        participants_data = json.load(file)

    with projects_path.open("r", encoding="utf-8") as file:
        projects_data = json.load(file)

    participants = tuple(
        Participant.model_validate(item)
        for item in participants_data
    )

    projects = tuple(
        Project.model_validate(item)
        for item in projects_data
    )

    catalog = Catalog(
        participants=participants,
        projects=projects,
    )

    window_builder = WindowBuilder(catalog)

    finding_service = FindingService(finding_repository)
    
    settings = load_settings()
    
    provider = VseLlmProvider(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
    )

    llm_analyzer = LlmSituationAnalyzer(
        provider=provider,
        system_prompt_path=PROMPT_PATH,
        max_output_tokens=settings.max_output_tokens,
    )
    
    llm_detector = LlmSituationDetector(
        analyzer=llm_analyzer,
        catalog=catalog,
    )
    
    
    analysis_service = AnalysisService(
        message_repository=message_repository,
        finding_service=finding_service,
        window_builder=window_builder,
        detectors=(
            # UnansweredDetector(),
            llm_detector,
        ),
    )

    import_service = MessageImportService(
        repository=message_repository,
    )

    inbox_service = InboxService(finding_repository)

    report_service = ReportService(
        repository=finding_repository,
    )

    return ApplicationContainer(
        import_service=import_service,
        analysis_service=analysis_service,
        inbox_service=inbox_service,
        report_service=report_service,
    )
