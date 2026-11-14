"""Flask app for the Healthcare Decision Intelligence dashboard.

    pip install -r web/requirements.txt
    python web/app.py            # http://127.0.0.1:5000

It serves the static pages in web/static/ plus a small JSON API. The same pages
also work without this server (see web/README.md), using web/static/data.json.
"""
import os

from flask import Flask, jsonify, request, send_from_directory

from build_data import Model, build

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(HERE, "static"), static_url_path="")
model = Model()  # the Task 2.2 logistic model, fitted once at start-up


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", mode="live")


@app.get("/api/data")
def data():
    return jsonify(build(model))


def _param(name, default, lo, hi):
    """Parse a bounded float query parameter; reject anything else."""
    raw = request.args.get(name, default)
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number" % name)
    if not lo <= val <= hi:
        raise ValueError("%s must be between %s and %s" % (name, lo, hi))
    return val


@app.get("/api/threshold")
def threshold():
    """Confusion cells and money cost for one alert threshold (tau in 0..1)."""
    try:
        tau = _param("tau", 0.5, 0.0, 1.0)
        false_alarm = _param("false_alarm", 50, 0, 1_000_000)
        missed = _param("missed", 400, 0, 1_000_000)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    cells = model.at(round(tau * 100))
    for part in cells.values():
        part["cost"] = false_alarm * part["fp"] + missed * part["fn"]
    return jsonify(tau=round(tau * 100) / 100, false_alarm=false_alarm, missed=missed, **cells)


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'"
    return resp


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
