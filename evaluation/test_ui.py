"""UI helpers that compute numbers: the onboarding funnel must reconcile with the data."""
from ui import components as ui


def test_funnel_reconciles_with_data(real_data):
    apps = real_data.applications
    stages, drops = ui.funnel_stages(len(apps), apps["step_reached"].value_counts().to_dict())
    values = [n for _, n in stages]
    assert values == [100, 90, 58, 41, 25]
    assert values[-1] == int((apps["application_status"] == "Activated").sum())  # last stage = activated merchants
    assert sum(n for _, n in drops) == 75  # every drop-off is a non-activated application
    assert max(drops, key=lambda d: d[1]) == ("KYC docs", 32)
    assert all(a >= b for a, b in zip(values, values[1:]))  # a funnel never widens


def test_funnel_figure_and_panel_render(real_data):
    apps = real_data.applications
    stages, drops = ui.funnel_stages(len(apps), apps["step_reached"].value_counts().to_dict())
    fig = ui.funnel_figure(stages, "sans-serif")
    assert list(fig.data[0].x) == [n for _, n in stages]
    assert "Where they drop off" in ui.dropoff_panel(drops, {})
