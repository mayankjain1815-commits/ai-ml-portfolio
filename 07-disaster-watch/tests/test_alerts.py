"""Tests for alert engine."""

from disaster_watch.alert_engine import AlertEngine
from disaster_watch.risk_model import score_forecast
from disaster_watch.forecast_gen import generate_forecast


def test_alert_engine_creates_alerts():
    forecast = generate_forecast(seed=13, hours=72)
    scored = score_forecast(forecast)
    engine = AlertEngine()
    alerts = engine.issue_alerts(scored)
    assert isinstance(alerts, list)
    # With storm ramp, we expect alerts
    for a in alerts:
        assert "alert_id" in a
        assert "severity" in a
        assert "location" in a
        assert a["severity"] in ["moderate", "high", "critical"]
