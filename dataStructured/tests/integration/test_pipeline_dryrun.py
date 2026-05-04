"""End-to-end dry-run: seed a brief, drive the pipeline by file presence checks.

This test exercises the orchestrator's idempotency logic, not the LLM employees.
"""
import json
import shutil
from pathlib import Path

from scripts.ceo_orchestrator import next_pipeline_step
from scripts.lib.atomic_io import write_json_atomic


def test_pipeline_state_machine_progresses(tmp_path):
    # Seed: only brief exists
    opps = tmp_path / "state" / "opportunities"
    opps.mkdir(parents=True)
    seed = json.loads((Path(__file__).parents[1] / "fixtures" / "seed_brief.json").read_text())
    write_json_atomic(opps / "2026-05-04-smoke-test-niche.json", seed)

    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "data-engineer"

    # Add raw CSV
    ds = tmp_path / "state" / "datasets" / "smoke-test-niche"
    ds.mkdir(parents=True)
    (ds / "raw-2026-05-04.csv").write_text("id,a,source_url\n1,x,https://example.com\n")
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "data-steward"

    # Add clean CSV
    (ds / "clean-2026-05-04.csv").write_text("id,a,source_url\n1,x,https://example.com\n")
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "compliance-officer"

    # Add ledger PASS
    ledger = tmp_path / "state" / "ethics-ledger"
    ledger.mkdir(parents=True)
    (ledger / "2026-05-04-smoke-test-niche.json").write_text('{"verdict": "PASS"}')
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "engineer"

    # Add launch report SHIPPED
    products = tmp_path / "state" / "products" / "smoke-test-niche"
    products.mkdir(parents=True)
    (products / "launch-report.json").write_text('{"status": "SHIPPED"}')
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "done"
