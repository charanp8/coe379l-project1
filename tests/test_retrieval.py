def test_exact_training_terms_are_retrieved(environment):
    result = environment.dispatch(
        "search_lab_documents",
        {"query": "laser cutter laser_safety", "top_k": 3},
    )
    assert result.ok
    ids = [item["passage_id"] for item in result.data["passages"]]
    assert "TRN-210#laser-cutter" in ids
