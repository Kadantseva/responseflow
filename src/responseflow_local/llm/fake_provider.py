from .models import LlmCallResult
from .provider import LlmRequest


class FakeLlmProvider:
    def __init__(self, result: LlmCallResult) -> None:
        self._result = result
        self.calls: list[LlmRequest] = []

    def complete(self, request: LlmRequest) -> LlmCallResult:
        self.calls.append(request)
        return self._result