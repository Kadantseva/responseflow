from collections.abc import Callable
from time import sleep

from .provider import LlmProvider, LlmRequest
from .models import LlmCallResult
from .vsellm_provider import TemporaryLlmError


class RetryingLlmProvider(LlmProvider):
    def __init__(self, delegate: LlmProvider, attempts: int = 3,
                 wait: Callable[[float], None] = sleep) -> None:
        if attempts < 1:
            raise ValueError("Число попыток должно быть положительным")
        self._delegate = delegate
        self._attempts = attempts
        self._wait = wait

    def complete(self, request: LlmRequest) -> LlmCallResult:
        for attempt in range(self._attempts):
            try:
                return self._delegate.complete(request)
            except TemporaryLlmError:
                if attempt == self._attempts - 1:
                    raise
                self._wait(2 ** attempt)
        raise AssertionError("Недостижимая ветвь")
