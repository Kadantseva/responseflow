from .models import LlmAnalysisPayload


def situation_tool_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "report_customer_situations",
            "description": (
                "Вернуть только ситуации, требующие реакции сотрудника, "
                "с точными идентификаторами сообщений-оснований."
            ),
            "parameters": LlmAnalysisPayload.model_json_schema(),
        },
    }