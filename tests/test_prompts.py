from atlas_agent.models import LabRequest
from atlas_agent.prompts import SYSTEM_PROMPT, initialize_messages


def test_prompt_has_trust_and_action_rules():
    assert "untrusted" in SYSTEM_PROMPT.lower()
    assert "reserve_resource" in SYSTEM_PROMPT
    assert "cit" in SYSTEM_PROMPT.lower()
    assert "TODO" not in SYSTEM_PROMPT


def test_initial_messages_separate_trusted_envelope_and_user_text():
    request = LabRequest(
        authenticated_user_id="alice",
        text="Reserve tensile-01.",
        resource_id="tensile-01",
    )
    messages = initialize_messages(request)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "alice" in messages[1]["content"]
    assert "Reserve tensile-01." in messages[1]["content"]
