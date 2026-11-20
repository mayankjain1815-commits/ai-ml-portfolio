"""Tests for forecast generation."""

from disaster_watch.forecast_gen import generate_forecast


def test_generate_forecast_shape():
    forecast = generate_forecast(seed=13, hours=24)
    assert len(forecast) == 6 * 24  # 6 areas * 24 hours
    row = forecast[0]
    for key in ["timestamp", "area_id", "rain_mm_h", "temperature_c", "humidity_pct", "wind_kph", "pressure_hpa"]:
        assert key in row


def test_forecast_deterministic():
    f1 = generate_forecast(seed=13, hours=12)
    f2 = generate_forecast(seed=13, hours=12)
    assert f1 == f2
