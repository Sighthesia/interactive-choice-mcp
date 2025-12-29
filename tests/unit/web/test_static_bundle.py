"""Smoke tests for static bundle routes."""

import pytest
from fastapi.testclient import TestClient

from src.web.server import WebChoiceServer
from src.web.bundler import get_asset_bundle


class TestStaticBundleRoutes:
    """Smoke tests for the static asset bundle endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the web server."""
        server = WebChoiceServer()
        return TestClient(server.app)

    def test_static_bundle_route_returns_css(self, client):
        """Verify CSS bundle route returns valid CSS with correct headers."""
        bundle = get_asset_bundle()
        response = client.get(f"/static/bundle.{bundle.css_hash}.css")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/css; charset=utf-8"
        assert "max-age=31536000" in response.headers["cache-control"]
        assert "immutable" in response.headers["cache-control"]
        assert response.headers["etag"] == f'"{bundle.css_hash}"'
        assert bundle.css in response.text

    def test_static_bundle_route_returns_js(self, client):
        """Verify JS bundle route returns valid JS with correct headers."""
        bundle = get_asset_bundle()
        response = client.get(f"/static/bundle.{bundle.js_hash}.js")
        
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
        assert "max-age=31536000" in response.headers["cache-control"]
        assert "immutable" in response.headers["cache-control"]
        assert response.headers["etag"] == f'"{bundle.js_hash}"'
        assert bundle.js in response.text

    def test_invalid_css_hash_returns_404(self, client):
        """Verify invalid CSS hash returns 404."""
        response = client.get("/static/bundle.invalidhash.css")
        assert response.status_code == 404

    def test_invalid_js_hash_returns_404(self, client):
        """Verify invalid JS hash returns 404."""
        response = client.get("/static/bundle.invalidhash.js")
        assert response.status_code == 404

    def test_bundle_content_is_not_empty(self, client):
        """Verify bundle content is substantial (smoke check)."""
        bundle = get_asset_bundle()
        
        css_response = client.get(f"/static/bundle.{bundle.css_hash}.css")
        js_response = client.get(f"/static/bundle.{bundle.js_hash}.js")
        
        # CSS should have reasonable content (at least variables and basic styles)
        assert len(css_response.text) > 1000, "CSS bundle seems too small"
        
        # JS should have reasonable content (at least bootstrap and helpers)
        assert len(js_response.text) > 1000, "JS bundle seems too small"
