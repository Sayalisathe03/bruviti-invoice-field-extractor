"""Tests for GET /health probe and GET / single-page UI."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_returns_200_and_exact_json():
    """Verify GET /health returns HTTP 200 and exactly {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_root_serves_html_ui():
    """Verify GET / returns HTTP 200 and serves self-contained HTML page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html_content = response.text
    # Check essential UI components
    assert "Bruviti Invoice Field Extractor" in html_content
    assert "fileInput" in html_content
    assert "extractBtn" in html_content
    assert "jsonViewer" in html_content
    # Confirm no external script or style CDNs are referenced (must be offline)
    assert "http://" not in html_content
    assert "https://" not in html_content
