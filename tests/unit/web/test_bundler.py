"""Tests for the asset bundler module."""

import pytest
from pathlib import Path

from src.web.bundler import (
    AssetBundle,
    get_asset_bundle,
    get_css_bundle,
    get_js_bundle,
    get_bundle_hash,
)


class TestAssetBundle:
    """Tests for the AssetBundle named tuple and bundler functions."""

    def test_get_asset_bundle_returns_namedtuple(self):
        """Verify get_asset_bundle returns an AssetBundle instance."""
        bundle = get_asset_bundle()
        assert isinstance(bundle, AssetBundle)

    def test_bundle_has_css_content(self):
        """Verify bundle contains non-empty CSS content."""
        bundle = get_asset_bundle()
        assert bundle.css, "CSS content should not be empty"
        assert "var(--" in bundle.css, "CSS should contain CSS variables"

    def test_bundle_has_js_content(self):
        """Verify bundle contains non-empty JS content."""
        bundle = get_asset_bundle()
        assert bundle.js, "JS content should not be empty"
        assert "window.mcpData" in bundle.js or "function" in bundle.js

    def test_bundle_has_valid_hashes(self):
        """Verify bundle hashes are 12-character hex strings."""
        bundle = get_asset_bundle()
        
        assert len(bundle.css_hash) == 12, "CSS hash should be 12 chars"
        assert len(bundle.js_hash) == 12, "JS hash should be 12 chars"
        assert len(bundle.combined_hash) == 12, "Combined hash should be 12 chars"
        
        # Verify hex format
        int(bundle.css_hash, 16)  # Should not raise
        int(bundle.js_hash, 16)
        int(bundle.combined_hash, 16)

    def test_bundle_caching(self):
        """Verify bundle is cached (same instance returned)."""
        bundle1 = get_asset_bundle()
        bundle2 = get_asset_bundle()
        assert bundle1 is bundle2, "Bundle should be cached"

    def test_css_includes_all_manifest_files(self):
        """Verify CSS bundle includes content from all manifest files."""
        bundle = get_asset_bundle()
        # Check for markers that indicate files were concatenated
        assert "base.css" in bundle.css or ":root" in bundle.css
        assert "layout" in bundle.css.lower() or ".layout" in bundle.css
        assert "components" in bundle.css.lower() or ".card" in bundle.css

    def test_js_includes_all_manifest_files(self):
        """Verify JS bundle includes content from all manifest files."""
        bundle = get_asset_bundle()
        # Check for functions from different modules
        assert "bootstrap" in bundle.js.lower() or "mcpData" in bundle.js
        assert "i18n" in bundle.js.lower() or "function t(" in bundle.js


class TestBundleHelpers:
    """Tests for individual bundle helper functions."""

    def test_get_css_bundle_returns_string(self):
        """Verify get_css_bundle returns CSS content string."""
        css = get_css_bundle()
        assert isinstance(css, str)
        assert css  # Not empty

    def test_get_js_bundle_returns_string(self):
        """Verify get_js_bundle returns JS content string."""
        js = get_js_bundle()
        assert isinstance(js, str)
        assert js  # Not empty

    def test_get_bundle_hash_returns_combined(self):
        """Verify get_bundle_hash returns the combined hash."""
        hash_val = get_bundle_hash()
        bundle = get_asset_bundle()
        assert hash_val == bundle.combined_hash
