"""UI helpers that compute numbers: the onboarding funnel must reconcile with the data."""
from ui import components as ui


def _stages(real_data):
    apps = real_data.applications
    return ui.funnel_stages(len(apps), apps["step_reached"].value_counts().to_dict())


def test_funnel_reconciles_with_data(real_data):
    stages, pending = _stages(real_data)
    assert [s for s, _, _ in stages] == ui.STEPS
    assert [r for _, r, _ in stages] == [100, 90, 58, 41, 25]          # reached each step
    assert [p for _, _, p in stages] == [10, 32, 17, 16, 25]           # pending there (last = live)
    apps = real_data.applications
    assert stages[-1][2] == int((apps["application_status"] == "Activated").sum())
    assert sum(p for _, p in pending) == 75                            # every pending case is non-activated
    assert max(pending, key=lambda d: d[1]) == ("KYC docs", 32)
    shares = {s: round(p / 75, 2) for s, p in pending}
    assert shares == {"Business details": 0.13, "KYC docs": 0.43, "Bank verification": 0.23, "Website/App review": 0.21}


def test_funnel_labels_show_pending_share(real_data):
    stages, pending = _stages(real_data)
    fig = ui.funnel_figure(stages, "sans-serif")
    text = list(fig.data[0].text)
    assert text[1] == "<b>32 pending</b>  ·  43% of stuck"
    assert text[-1] == "<b>25 live</b>"
    panel = ui.dropoff_panel(pending, {})
    assert "Pending by stage" in panel and "43%" in panel and "32 of 75 pending" in panel
