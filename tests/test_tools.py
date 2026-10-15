def test_reservation_tool_enforces_conflict_but_not_training_policy(environment):
    conflict = environment.dispatch(
        "reserve_resource",
        {
            "user_id": "bob",
            "project_id": "polymer-study",
            "resource_id": "tensile-01",
            "start": "2026-10-15T13:30:00",
            "end": "2026-10-15T14:30:00",
        },
    )
    assert not conflict.ok
    assert conflict.error_code == "reservation_conflict"


def test_unknown_tool_is_rejected(environment):
    result = environment.dispatch("delete_all_reservations", {})
    assert not result.ok
    assert result.error_code == "unknown_tool"
