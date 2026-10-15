def test_public_scripted_benchmark_passes(project_root):
    from atlas_agent.public_benchmark import run_public_benchmark

    records = run_public_benchmark(project_root)
    assert len(records) == 6
    assert all(
        record.run.response.status == record.expected_status for record in records
    )
