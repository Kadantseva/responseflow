from pathlib import Path

from responseflow_local.domain.models import ConversationWindow
from .models import AnalysisResult, LlmSituation
from .prompt_builder import build_request
from .provider import LlmProvider
from .response_parser import parse_payload


class UnknownEvidenceError(ValueError):
    pass


class LlmSituationAnalyzer:
    def __init__(self, provider: LlmProvider, system_prompt_path: Path,
                 max_output_tokens: int = 1200,
                 confidence_threshold: float = 0.60,
                 max_situations: int = 20) -> None:
        self._provider = provider
        self._system_prompt_path = system_prompt_path
        self._max_output_tokens = max_output_tokens
        self._confidence_threshold = confidence_threshold
        self._max_situations = max_situations

    def analyze(self, window: ConversationWindow,
                project_context: str) -> AnalysisResult:
        request = build_request(
            window, project_context, self._system_prompt_path,
            self._max_output_tokens,
        )
        call = self._provider.complete(request)
        payload = parse_payload(call)
        if len(payload.situations) > self._max_situations:
            raise ValueError("LLM вернула слишком много ситуаций")
        available = {message.external_id for message in window.messages}
        accepted: list[LlmSituation] = []
        for situation in payload.situations:
            evidence = tuple(dict.fromkeys(situation.evidence_message_ids))
            missing = [item for item in evidence if item not in available]
            if missing:
                raise UnknownEvidenceError(
                    f"В окне нет сообщений-оснований: {missing}"
                )
            if situation.confidence < self._confidence_threshold:
                continue
            accepted.append(situation.model_copy(update={
                "evidence_message_ids": evidence,
            }))
        return AnalysisResult(
            situations=tuple(accepted),
            provider=call.provider,
            model=call.model,
            prompt_version="system-prompt-v1",
            usage=call.usage,
        )