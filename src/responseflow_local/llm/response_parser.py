import json

from pydantic import ValidationError

from .models import LlmAnalysisPayload, LlmCallResult


class InvalidStructuredOutputError(ValueError):
    pass


def parse_payload(result: LlmCallResult) -> LlmAnalysisPayload:
    try:
        raw = json.loads(result.raw_arguments)
        return LlmAnalysisPayload.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as error:
        raise InvalidStructuredOutputError("Неверный структурированный ответ LLM") from error