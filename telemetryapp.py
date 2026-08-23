from flask import Flask, render_template, jsonify
import pandas as pd
import os

app = Flask(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), "telemetry.csv")

# sea to air level pressure in pascals
SEA_LEVEL_PRESSURE_PA = 101325.0

# Acceleration above this (~2x gravity) counts as liftoff.
LIFTOFF_ACCEL_THRESHOLD_MPS2 = 20.0

# Every column except GPS_TIME should be a number.
NUMERIC_COLUMNS = [
    "TIMESTAMP", "PRESSURE", "GYRO_X", "GYRO_Y", "GYRO_Z",
    "ACCEL_X", "ACCEL_Y", "ACCEL_Z", "VOLTAGE", "CURRENT",
    "GPS_ALTITUDE", "GPS_LATITUDE", "GPS_LONGITUDE", "GPS_SATS",
]


def _read_dataframe():
    """Load the CSV and add the computed columns."""
    df = pd.read_csv(CSV_PATH)

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # (0, 0) means no GPS fix, not a real spot
    gps_dropout = (df["GPS_LATITUDE"] == 0) & (df["GPS_LONGITUDE"] == 0)
    df.loc[gps_dropout, ["GPS_LATITUDE", "GPS_LONGITUDE", "GPS_ALTITUDE"]] = float("nan")

    # magnitude = sqrt(x^2 + y^2 + z^2)
    df["ACCEL_MAGNITUDE"] = (
        df["ACCEL_X"] ** 2 + df["ACCEL_Y"] ** 2 + df["ACCEL_Z"] ** 2
    ) ** 0.5

    df["GYRO_MAGNITUDE"] = (
        df["GYRO_X"] ** 2 + df["GYRO_Y"] ** 2 + df["GYRO_Z"] ** 2
    ) ** 0.5

    # Estimate altitude from pressure, as a check against the GPS altitude.
    df["ALTITUDE_BARO"] = 44330.0 * (
        1.0 - (df["PRESSURE"] / SEA_LEVEL_PRESSURE_PA) ** (1.0 / 5.255)
    )

    return df


def load_telemetry():
    """Return telemetry rows"""
    df = _read_dataframe()
    df = df.astype(object).where(pd.notnull(df), None)
    return df.to_dict(orient="records")


def _max_with_timestamp(df, column):
    """Find where column peaks and return its value + timestamp."""
    series = df[column]
    if not series.notna().any():
        return None
    idx = series.idxmax()
    return {
        "value": float(series.loc[idx]),
        "timestamp": float(df.loc[idx, "TIMESTAMP"]),
    }


def load_summary():
    """Flight highlights peak readings +liftoff/apogee/landing times."""
    df = _read_dataframe()

    max_acceleration = _max_with_timestamp(df, "ACCEL_MAGNITUDE")
    max_angular_velocity = _max_with_timestamp(df, "GYRO_MAGNITUDE")
    apogee = _max_with_timestamp(df, "GPS_ALTITUDE")

    liftoff_rows = df[df["ACCEL_MAGNITUDE"] > LIFTOFF_ACCEL_THRESHOLD_MPS2]
    liftoff = (
        {"timestamp": float(liftoff_rows.iloc[0]["TIMESTAMP"])}
        if not liftoff_rows.empty
        else None
    )

    landing = (
        {"timestamp": float(df["TIMESTAMP"].max())}
        if df["TIMESTAMP"].notna().any()
        else None
    )

    return {
        "max_acceleration": max_acceleration,
        "max_angular_velocity": max_angular_velocity,
        "events": {
            "liftoff": liftoff,
            "apogee": (
                {"timestamp": apogee["timestamp"], "altitude": apogee["value"]}
                if apogee
                else None
            ),
            "landing": landing,
        },
    }


@app.route("/")
def index():
    """Serve the main webpage."""
    return render_template("index.html")


@app.route("/api/telemetry")
def api_telemetry():
    """Return the telemetry data as JSON for the frontend to consume."""
    if not os.path.exists(CSV_PATH):
        return jsonify({"error": "Can't find telemetry.csv."}), 404

    try:
        data = load_telemetry()
    except pd.errors.EmptyDataError:
        return jsonify([])
    except Exception as exc:
        return jsonify({"error": f"Couldn't read telemetry.csv: {exc}"}), 500

    return jsonify(data)


@app.route("/api/summary")
def api_summary():
    """Return flight summary stats """
    if not os.path.exists(CSV_PATH):
        return jsonify({"error": "Can't find telemetry.csv."}), 404

    try:
        summary = load_summary()
    except pd.errors.EmptyDataError:
        return jsonify({
            "max_acceleration": None,
            "max_angular_velocity": None,
            "events": {"liftoff": None, "apogee": None, "landing": None},
        })
    except Exception as exc:
        return jsonify({"error": f"Couldn't read telemetry.csv: {exc}"}), 500

    return jsonify(summary)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
