from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from .models import LlmCallResult, LlmUsage
from .provider import LlmProvider, LlmRequest


class TemporaryLlmError(RuntimeError):
    pass


class InvalidLlmResponseError(RuntimeError):
    pass


class VseLlmProvider(LlmProvider):
    def __init__(self, api_key: str, base_url: str, model: str,
                 timeout_seconds: float) -> None:
        self._model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def complete(self, request: LlmRequest) -> LlmCallResult:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[item.model_dump() for item in request.messages],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": request.tool_name,
                        "description": request.tool_description,
                        "parameters": request.tool_parameters,
                    },
                }],
                tool_choice={
                    "type": "function",
                    "function": {"name": request.tool_name},
                },
                max_tokens=request.max_output_tokens,
            )
        except (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        ) as error:
            raise TemporaryLlmError("Временная ошибка вызова LLM") from error

        message = response.choices[0].message
        if not message.tool_calls:
            raise InvalidLlmResponseError("Модель не вызвала обязательную функцию")
        call = message.tool_calls[0]
        if call.function.name != request.tool_name:
            raise InvalidLlmResponseError("Модель вызвала неизвестную функцию")
        usage = response.usage
        return LlmCallResult(
            provider="vsellm",
            model=self._model,
            raw_arguments=call.function.arguments,
            usage=LlmUsage(
                input_tokens=usage.prompt_tokens if usage else None,
                output_tokens=usage.completion_tokens if usage else None,
            ),
        )