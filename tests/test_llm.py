from atlas_agent.agent_models import DecisionAdapter, ToolCallDecision
from atlas_agent.llm import OpenAICompatibleLLM, ScriptedLLM


def test_scripted_llm_returns_typed_decision_and_records_messages():
    scripted = ScriptedLLM(
        [
            {
                "kind": "tool_call",
                "tool": "get_user_authorizations",
                "arguments": {"user_id": "alice"},
                "reasoning_summary": "Check authorization.",
            }
        ]
    )
    messages = [{"role": "user", "content": "A request"}]
    decision = scripted.generate(messages=messages, response_model=DecisionAdapter)
    messages[0]["content"] = "changed after the call"

    assert isinstance(decision, ToolCallDecision)
    assert scripted.calls[0][0]["content"] == "A request"


def test_live_adapter_uses_same_typed_interface_without_network():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"kind":"tool_call",'
                                '"tool":"get_user_authorizations",'
                                '"arguments":{"user_id":"alice"},'
                                '"reasoning_summary":"Check authorization."}'
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self):
            self.payload = None

        def post(self, url, *, headers, json):
            self.payload = {"url": url, "headers": headers, "json": json}
            return FakeResponse()

    client = FakeClient()
    llm = OpenAICompatibleLLM(
        base_url="https://inference.example/v1",
        model="course-model",
        client=client,
    )
    decision = llm.generate(
        messages=[{"role": "user", "content": "A request"}],
        response_model=DecisionAdapter,
    )
    assert isinstance(decision, ToolCallDecision)
    assert client.payload["json"]["response_format"]["type"] == "json_schema"
