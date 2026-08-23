import math

import pytest

import telemetryapp


HEADER = (
    "TIMESTAMP,PRESSURE,GYRO_X,GYRO_Y,GYRO_Z,ACCEL_X,ACCEL_Y,ACCEL_Z,"
    "VOLTAGE,CURRENT,GPS_TIME,GPS_ALTITUDE,GPS_LATITUDE,GPS_LONGITUDE,GPS_SATS"
)


@pytest.fixture
def client():
    telemetryapp.app.testing = True
    return telemetryapp.app.test_client()


def write_csv(tmp_path, rows):
    csv_path = tmp_path / "telemetry.csv"
    csv_path.write_text(HEADER + "\n" + "\n".join(rows) + "\n")
    return csv_path


def test_acceleration_magnitude_is_calculated_correctly(tmp_path, monkeypatch):
    csv_path = write_csv(
        tmp_path,
        ["0.0,92446.6,-0.02,0.0,-0.01,3,4,0,8.2,0.15,17:03:02,820.4,38.3757,-79.6074,12"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    rows = telemetryapp.load_telemetry()

    assert rows[0]["ACCEL_MAGNITUDE"] == pytest.approx(5.0)


def test_gyro_magnitude_is_calculated_correctly(tmp_path, monkeypatch):
    csv_path = write_csv(
        tmp_path,
        ["0.0,92446.6,3,4,0,-0.1,0.4,-9.61,8.2,0.15,17:03:02,820.4,38.3757,-79.6074,12"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    rows = telemetryapp.load_telemetry()

    assert rows[0]["GYRO_MAGNITUDE"] == pytest.approx(5.0)


def test_altitude_baro_matches_gps_altitude_roughly(tmp_path, monkeypatch):
    # At the standard sea-level reference pressure, estimated altitude is 0.
    csv_path = write_csv(
        tmp_path,
        ["0.0,101325,0,0,0,0,0,-9.8,8.2,0.15,17:03:02,0,38.3757,-79.6074,12"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    rows = telemetryapp.load_telemetry()

    assert rows[0]["ALTITUDE_BARO"] == pytest.approx(0.0, abs=1e-6)


def test_gps_null_island_dropout_is_treated_as_missing(tmp_path, monkeypatch):
    csv_path = write_csv(
        tmp_path,
        ["5.0,90155.3,0.74,0,0,-6.78,-0.13,19.3,8.2,0.14,17:03:07,0,0,0,12"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    rows = telemetryapp.load_telemetry()

    assert rows[0]["GPS_LATITUDE"] is None
    assert rows[0]["GPS_LONGITUDE"] is None
    assert rows[0]["GPS_ALTITUDE"] is None
    # Non-GPS readings from the same sample are still valid.
    assert rows[0]["PRESSURE"] == pytest.approx(90155.3)


def test_missing_values_become_none(tmp_path, monkeypatch):
    csv_path = write_csv(
        tmp_path,
        ["1.0,,-0.03,0.0,-0.02,,0.39,-9.61,8.2,0.14,17:03:03,820.4,38.3757,-79.6074,12"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    rows = telemetryapp.load_telemetry()

    assert rows[0]["PRESSURE"] is None
    assert rows[0]["ACCEL_X"] is None
    # A missing axis means the magnitude can't be computed either.
    assert rows[0]["ACCEL_MAGNITUDE"] is None


def test_invalid_values_become_none(tmp_path, monkeypatch):
    csv_path = write_csv(
        tmp_path,
        ["2.0,92443.5,-0.03,0.0,-0.02,not_a_number,0.35,-9.59,8.2,0.15,17:03:04,820.3,38.3757,-79.6074,12"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    rows = telemetryapp.load_telemetry()

    assert rows[0]["ACCEL_X"] is None
    assert rows[0]["ACCEL_MAGNITUDE"] is None
    # A non-numeric string column (GPS_TIME) is left untouched.
    assert rows[0]["GPS_TIME"] == "17:03:04"


def test_no_nan_reaches_json_output(tmp_path, monkeypatch):
    """NaN is not valid JSON; every field must be a real value or None."""
    csv_path = write_csv(
        tmp_path,
        ["3.0,,-0.03,0.0,-0.02,,,-9.59,8.2,0.15,17:03:05,,38.3757,-79.6074,"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    rows = telemetryapp.load_telemetry()

    for value in rows[0].values():
        assert not (isinstance(value, float) and math.isnan(value))


def test_api_telemetry_returns_rows(client, tmp_path, monkeypatch):
    csv_path = write_csv(
        tmp_path,
        ["0.0,92446.6,-0.02,0.0,-0.01,-0.1,0.4,-9.61,8.2,0.15,17:03:02,820.4,38.3757,-79.6074,12"],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    resp = client.get("/api/telemetry")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert "ACCEL_MAGNITUDE" in data[0]


def test_api_telemetry_missing_file_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(tmp_path / "does_not_exist.csv"))

    resp = client.get("/api/telemetry")

    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_api_telemetry_empty_file_returns_empty_list(client, tmp_path, monkeypatch):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("")
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    resp = client.get("/api/telemetry")

    assert resp.status_code == 200
    assert resp.get_json() == []


def test_index_route_serves_html(client):
    resp = client.get("/")

    assert resp.status_code == 200
    assert b"CanSat" in resp.data


def test_api_summary_reports_peaks_and_events(client, tmp_path, monkeypatch):
    csv_path = write_csv(
        tmp_path,
        [
            "0.0,101325,0,0,0,0,0,-9.8,8.2,0.15,17:03:00,0,38.3757,-79.6074,12",
            "1.0,101300,0,0,0,0,0,25,8.2,0.15,17:03:01,100,38.3757,-79.6074,12",
            "2.0,100000,0,0,0,0,0,-9.8,8.2,0.15,17:03:02,500,38.3757,-79.6074,12",
            "3.0,101325,0,0,0,0,0,-9.8,8.2,0.15,17:03:03,50,38.3757,-79.6074,12",
        ],
    )
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    resp = client.get("/api/summary")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["max_acceleration"]["timestamp"] == pytest.approx(1.0)
    assert data["events"]["liftoff"]["timestamp"] == pytest.approx(1.0)
    assert data["events"]["apogee"]["timestamp"] == pytest.approx(2.0)
    assert data["events"]["apogee"]["altitude"] == pytest.approx(500)
    assert data["events"]["landing"]["timestamp"] == pytest.approx(3.0)


def test_api_summary_missing_file_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(tmp_path / "does_not_exist.csv"))

    resp = client.get("/api/summary")

    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_api_summary_empty_file_returns_none_fields(client, tmp_path, monkeypatch):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("")
    monkeypatch.setattr(telemetryapp, "CSV_PATH", str(csv_path))

    resp = client.get("/api/summary")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["max_acceleration"] is None
    assert data["events"]["liftoff"] is None
