"""Smoke test: the Streamlit app runs end to end from saved AI answers without errors."""
from streamlit.testing.v1 import AppTest

import config
from core import pipeline


def test_pipeline_rule_only_runs(real_data):
    run = pipeline.run(llm_mode="off")
    assert len(run.results) == 75 and run.llm.calls == 0
    assert list(run.work_queue["priority_rank"]) == sorted(run.work_queue["priority_rank"])


def test_app_renders_all_tabs_without_errors():
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, at.exception
    assert [t.label for t in at.tabs] == ["Overview", "Application work queue", "Merchant nudge review",
                                          "Evaluation & audit"]
    labels = {m.label: m.value for m in at.metric}
    assert labels["Non-activated"] == "75"
    assert not any("Send" in b.label for b in at.button)  # drafting tool only: no send action
