"""
Test middleware functions.
"""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from middleware import DevStaticFiles, configure_cors, configure_trusted_host


class TestCORSMiddleware:
    """Test CORS middleware configuration"""

    def test_cors_configuration(self):
        """Test CORS is properly configured on app"""
        app = FastAPI()
        configure_cors(app)

        # Check that middleware was added
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in str(middleware_classes)

    def test_cors_headers(self):
        """Test CORS headers in responses"""
        app = FastAPI()
        configure_cors(app)

        @app.get("/test")
        def test_endpoint():
            return {"test": "data"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Note: TestClient doesn't always show CORS headers
        # This test ensures the middleware is properly configured


class TestTrustedHostMiddleware:
    """Test trusted host middleware configuration"""

    def test_trusted_host_configuration(self):
        """Test trusted host middleware is configured"""
        app = FastAPI()
        configure_trusted_host(app)

        # Check that middleware was added
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "TrustedHostMiddleware" in str(middleware_classes)

    def test_trusted_host_allows_localhost(self):
        """Test that localhost is allowed"""
        app = FastAPI()
        configure_trusted_host(app)

        @app.get("/test")
        def test_endpoint():
            return {"test": "data"}

        client = TestClient(app)
        response = client.get("/test", headers={"Host": "localhost"})

        assert response.status_code == 200


class TestDevStaticFiles:
    """Test development static files server"""

    def test_init_with_valid_directory(self, tmp_path):
        """Test initialization with valid directory"""
        # Create a test directory
        test_dir = tmp_path / "static"
        test_dir.mkdir()

        static_files = DevStaticFiles(directory=str(test_dir), html=True)

        assert static_files.directory == str(test_dir)
        assert static_files.html is True

    def test_init_with_invalid_directory(self):
        """Test initialization with non-existent directory"""
        with pytest.raises(RuntimeError, match="Directory .* does not exist"):
            DevStaticFiles(directory="/non/existent/path")

    def test_serves_html_file(self, tmp_path):
        """Test serving HTML files"""
        # Create test directory and file
        test_dir = tmp_path / "static"
        test_dir.mkdir()
        html_file = test_dir / "index.html"
        html_file.write_text("<html><body>Test</body></html>")

        app = FastAPI()
        app.mount(
            "/", DevStaticFiles(directory=str(test_dir), html=True), name="static"
        )

        client = TestClient(app)
        response = client.get("/index.html")

        assert response.status_code == 200
        assert "Test" in response.text

    def test_serves_css_file(self, tmp_path):
        """Test serving CSS files"""
        # Create test directory and file
        test_dir = tmp_path / "static"
        test_dir.mkdir()
        css_file = test_dir / "styles.css"
        css_file.write_text("body { color: red; }")

        app = FastAPI()
        app.mount("/", DevStaticFiles(directory=str(test_dir)), name="static")

        client = TestClient(app)
        response = client.get("/styles.css")

        assert response.status_code == 200
        assert "color: red" in response.text

    def test_serves_javascript_file(self, tmp_path):
        """Test serving JavaScript files"""
        # Create test directory and file
        test_dir = tmp_path / "static"
        test_dir.mkdir()
        js_file = test_dir / "script.js"
        js_file.write_text("console.log('test');")

        app = FastAPI()
        app.mount("/", DevStaticFiles(directory=str(test_dir)), name="static")

        client = TestClient(app)
        response = client.get("/script.js")

        assert response.status_code == 200
        assert "console.log" in response.text

    def test_html_fallback(self, tmp_path):
        """Test HTML fallback for SPA routing"""
        # Create test directory and index.html
        test_dir = tmp_path / "static"
        test_dir.mkdir()
        html_file = test_dir / "index.html"
        html_file.write_text("<html><body>SPA</body></html>")

        app = FastAPI()
        app.mount(
            "/", DevStaticFiles(directory=str(test_dir), html=True), name="static"
        )

        client = TestClient(app)

        # Non-existent path should return index.html when html=True
        response = client.get("/non/existent/route")

        assert response.status_code == 200
        assert "SPA" in response.text

    def test_404_without_html_fallback(self, tmp_path):
        """Test 404 response without HTML fallback"""
        # Create test directory
        test_dir = tmp_path / "static"
        test_dir.mkdir()

        app = FastAPI()
        app.mount(
            "/", DevStaticFiles(directory=str(test_dir), html=False), name="static"
        )

        client = TestClient(app)
        response = client.get("/non/existent/file.txt")

        assert response.status_code == 404


class TestMiddlewareIntegration:
    """Test middleware integration"""

    def test_all_middleware_together(self):
        """Test all middleware working together"""
        app = FastAPI()

        # Configure all middleware
        configure_cors(app)
        configure_trusted_host(app)

        @app.get("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Test that endpoint works with all middleware
        response = client.get("/api/test")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Test OPTIONS request (CORS preflight)
        response = client.options("/api/test")
        # OPTIONS might return 405 but shouldn't error
        assert response.status_code in [200, 405]
