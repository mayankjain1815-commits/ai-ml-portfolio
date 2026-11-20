"""Tests for risk model."""

from disaster_watch.risk_model import RiskModel, score_forecast
from disaster_watch.forecast_gen import generate_forecast


def test_risk_model_scoring():
    model = RiskModel()
    row = {
        "rain_mm_h": 40.0,
        "wind_kph": 80.0,
        "pressure_hpa": 995.0,
        "humidity_pct": 95.0,
        "visibility_km": 2.0,
        "terrain": "coastal_lowland",
    }
    result = model.score_row(row)
    assert 0 <= result["risk_index"] <= 100
    assert result["risk_level"] in ["low", "moderate", "high", "critical"]
    assert isinstance(result["triggers"], list)


def test_score_forecast_adds_risk():
    forecast = generate_forecast(seed=13, hours=6)
    scored = score_forecast(forecast)
    assert len(scored) == len(forecast)
    assert "risk_index" in scored[0]
    assert "risk_level" in scored[0]
