
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from responseflow_local.application.analyze import AnalysisService
from responseflow_local.application.import_messages import MessageImportService
from responseflow_local.application.report import ReportService
from responseflow_local.application.review import InboxService

from responseflow_local.storage.sqlite_repositories import SqliteFindingRepository
from responseflow_local.storage.sqlite_message_repository import SqliteMessageRepository
from responseflow_local.storage.sqlite import SqliteDatabase

from responseflow_local.detectors.unanswered import UnansweredDetector
from responseflow_local.detectors.fake_semantic_analyzer import (
    FakeSemanticAnalyzer,
)
from responseflow_local.detectors.semantic_situations import (
    SemanticSituationService,
)

from responseflow_local.llm.fake_provider import FakeLlmProvider
from responseflow_local.llm.models import LlmCallResult, LlmUsage
from responseflow_local.llm.settings import load_settings
from responseflow_local.llm.vsellm_provider import VseLlmProvider
from responseflow_local.llm.retrying_provider import RetryingLlmProvider
from responseflow_local.llm.analyzer import LlmSituationAnalyzer


load_dotenv()


@dataclass(frozen=True)
class ApplicationContainer:
    import_service: MessageImportService
    analysis_service: AnalysisService
    inbox_service: InboxService
    report_service: ReportService


def _build_llm_provider(fixture_root: Path):
    provider_name = os.getenv("LLM_PROVIDER", "fake").strip().lower()

    if provider_name == "fake":
        fixture_path = fixture_root / "llm_result.json"

        if fixture_path.exists():
            raw = json.loads(fixture_path.read_text(encoding="utf-8"))
            result = LlmCallResult.model_validate(raw)
        else:
            # Пустой валидный результат для локального запуска без API.
            result = LlmCallResult(
                provider="fake",
                model="fixture",
                raw_arguments='{"situations": []}',
                usage=LlmUsage(
                    input_tokens=0,
                    output_tokens=0,
                ),
            )

        return FakeLlmProvider(result)

    if provider_name == "vsellm":
        settings = load_settings()

        provider = VseLlmProvider(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
        )

        return RetryingLlmProvider(provider)

    raise ValueError(
        "Неизвестный LLM_PROVIDER. Допустимые значения: fake, vsellm"
    )


def build_application(
    database_path: Path,
    fixture_root: Path,
) -> ApplicationContainer:
    database = SqliteDatabase(database_path)
    database.initialize()

    message_repository = SqliteMessageRepository(database)
    finding_repository = SqliteFindingRepository(database)

    # Построитель окон должен получать актуальные сообщения
    # и контекст проекта из репозиториев.
    from responseflow_local.application.windows import ConversationWindowBuilder
    from responseflow_local.domain.models import ConversationWindow

    window_builder = ConversationWindowBuilder(
        message_repository=message_repository,
    )

    # Анализаторы.
    unanswered_detector = UnansweredDetector()

    system_prompt_path = (
        Path(__file__).parent / "llm" / "system_prompt.txt"
    )

    llm_provider = _build_llm_provider(fixture_root)

    llm_analyzer = LlmSituationAnalyzer(
        provider=llm_provider,
        system_prompt_path=system_prompt_path,
    )

    # Адаптер LLM к общему интерфейсу SituationDetector
    # должен преобразовывать LlmSituation в FindingCandidate.
    from responseflow_local.detectors.semantic_llm import (
        SemanticLlmDetector,
    )

    semantic_detector = SemanticLlmDetector(
        analyzer=llm_analyzer,
        message_repository=message_repository,
    )

    detectors = (
        unanswered_detector,
        semantic_detector,
    )

    # Службы приложения.
    from responseflow_local.application.findings import FindingService

    finding_service = FindingService(finding_repository)

    analysis_service = AnalysisService(
        message_repository=message_repository,
        finding_service=finding_service,
        window_builder=window_builder,
        detectors=detectors,
    )

    import_service = MessageImportService(
        message_repository=message_repository,
    )

    inbox_service = InboxService(finding_repository)

    report_service = ReportService(
        finding_repository=finding_repository,
    )

    return ApplicationContainer(
        import_service=import_service,
        analysis_service=analysis_service,
        inbox_service=inbox_service,
        report_service=report_service,
    )
