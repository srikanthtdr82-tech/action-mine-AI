"""
test_webapp.py
Integration tests for Flask Web Application routes and API endpoints.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app


def test_flask_app():
    client = app.test_client()

    # 1. Test homepage
    res_home = client.get("/")
    assert res_home.status_code == 200
    assert b"ActionMine AI" in res_home.data
    print("  [PASS] GET / renders successfully with Competition Dashboard")

    # 2. Test favicon route (must not return 404)
    res_fav = client.get("/favicon.ico")
    assert res_fav.status_code == 204
    print("  [PASS] GET /favicon.ico returns 204 No Content (No red browser error)")

    # 3. Test extract API with valid transcript
    transcript = (
        "Carlos: I will update the API authentication documentation by tomorrow at 3 PM.\n"
        "Priya: We really need to redesign the user onboarding illustrations before the marketing push next Friday."
    )
    res_extract = client.post("/api/extract", json={"transcript": transcript, "meeting_date": "2026-11-10"})
    assert res_extract.status_code == 200
    data = res_extract.get_json()
    assert data["status"] == "success"
    assert len(data["action_items"]) == 2
    assert "analytics" in data
    assert data["analytics"]["total_tasks"] == 2
    print("  [PASS] POST /api/extract returns action items and team workload analytics")

    # 4. Test benchmark API
    res_bench = client.get("/api/benchmark")
    assert res_bench.status_code == 200
    bench_data = res_bench.get_json()
    assert bench_data["precision"] == 1.0
    assert bench_data["false_certainty_rate"] == 0.0
    print("  [PASS] GET /api/benchmark returns 100% precision and 0.0% false-certainty rate")

    # 5. Test iCalendar (.ics) export API
    sample_items = [
        {
            "task": "Update API docs",
            "owner": "Carlos",
            "deadline": "Tomorrow at 3 PM",
            "target_iso_date": "2026-11-11",
            "review_status": "Confirmed",
            "source_quote": "I will update the API docs"
        }
    ]
    res_cal = client.post("/api/export/calendar", json={"action_items": sample_items})
    assert res_cal.status_code == 200
    assert b"BEGIN:VCALENDAR" in res_cal.data
    assert b"SUMMARY:[Action Item] Update API docs" in res_cal.data
    print("  [PASS] POST /api/export/calendar produces valid RFC 5545 iCalendar data")


if __name__ == "__main__":
    print("\nRunning Web Application Integration Tests...")
    test_flask_app()
    print("\nAll Web Application tests passed with zero errors!\n")
