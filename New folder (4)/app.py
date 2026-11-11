"""
app.py
Competition-Grade Web Application Server for AI Meeting Action-Item Extractor.
Features:
  - Multi-engine extraction (Symbolic NLP & Neural AI)
  - Team workload & accountability analytics
  - 1-click Google Calendar / Apple Calendar (.ics) export
  - Benchmark evaluation suite with interactive confusion matrix
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extractor import extract_action_items_from_text, generate_icalendar, compute_team_workload
from src.evaluator import evaluate_predictions

app = Flask(__name__)


@app.route("/favicon.ico")
def favicon():
    """Suppresses browser 404 for favicon."""
    return Response(status=204)


@app.route("/")
def index():
    """Serves the main interactive dashboard."""
    return render_template("index.html")


@app.route("/api/extract", methods=["POST"])
def extract_api():
    """Extracts action items and returns structured items with workload analytics."""
    data = request.get_json() or {}
    transcript = data.get("transcript", "")
    meeting_date = data.get("meeting_date", "2026-11-10")
    engine = data.get("engine", "symbolic")

    if not transcript.strip():
        return jsonify({"error": "No transcript provided", "action_items": []}), 400

    items = extract_action_items_from_text(transcript, engine=engine, meeting_date=meeting_date)
    analytics = compute_team_workload(items)

    return jsonify({
        "status": "success",
        "engine": engine,
        "count": len(items),
        "meeting_date": meeting_date,
        "action_items": items,
        "analytics": analytics
    })


@app.route("/api/export/calendar", methods=["POST"])
def export_calendar_api():
    """Generates and downloads a standard RFC 5545 .ics calendar file."""
    data = request.get_json() or {}
    items = data.get("action_items", [])
    meeting_name = data.get("meeting_name", "Meeting Deliverables")

    ics_content = generate_icalendar(items, meeting_name=meeting_name)
    return Response(
        ics_content,
        mimetype="text/calendar",
        headers={"Content-Disposition": "attachment;filename=meeting_action_items.ics"}
    )


@app.route("/api/benchmark", methods=["GET"])
def benchmark_api():
    """Runs automated evaluation across gold-standard test meetings."""
    data_path = PROJECT_ROOT / "data" / "sample_transcripts.json"
    if not data_path.exists():
        return jsonify({"error": "Sample data not found"}), 404

    with open(data_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    all_gold = []
    all_pred = []

    for sample in samples:
        pred = extract_action_items_from_text(sample["transcript"])
        all_gold.extend(sample["expected_action_items"])
        all_pred.extend(pred)

    metrics = evaluate_predictions(all_gold, all_pred)
    return jsonify(metrics)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  AI Meeting Action-Item Extractor Web App Running!")
    print(f"  Local URL: http://127.0.0.1:{port}")
    print(f"  Mode: Competition-Grade Multi-Tab Dashboard")
    print(f"  Constraint: Zero-Guessing Rule Active")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
