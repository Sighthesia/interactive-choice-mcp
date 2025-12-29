"""Asset bundler for web frontend assets.

Reads the manifest.json and concatenates CSS/JS files into cached bundles
with content-based hashes for cache busting.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

__all__ = [
    "AssetBundle",
    "get_asset_bundle",
    "get_css_bundle",
    "get_js_bundle",
    "get_bundle_hash",
]

_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
_MANIFEST_PATH = _FRONTEND_DIR / "manifest.json"


class AssetBundle(NamedTuple):
    """Holds concatenated asset content and its hash."""
    css: str
    js: str
    css_hash: str
    js_hash: str
    combined_hash: str


def _compute_hash(content: str) -> str:
    """Compute a short SHA1 hash of content for cache busting."""
    return hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]


def _load_manifest() -> dict:
    """Load the asset manifest."""
    if not _MANIFEST_PATH.exists():
        return {"styles": [], "scripts": []}
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _concat_files(base_dir: Path, file_list: list[str]) -> str:
    """Concatenate files in order, adding section markers."""
    parts: list[str] = []
    for rel_path in file_list:
        file_path = base_dir / rel_path
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            parts.append(f"/* === {rel_path} === */\n{content}")
    return "\n\n".join(parts)


@lru_cache(maxsize=1)
def get_asset_bundle() -> AssetBundle:
    """Load and cache the assembled asset bundle.
    
    Returns an AssetBundle with concatenated CSS/JS and their hashes.
    The bundle is cached in memory; restart server to pick up changes.
    """
    manifest = _load_manifest()
    
    css_content = _concat_files(_FRONTEND_DIR, manifest.get("styles", []))
    js_content = _concat_files(_FRONTEND_DIR, manifest.get("scripts", []))
    
    css_hash = _compute_hash(css_content)
    js_hash = _compute_hash(js_content)
    combined_hash = _compute_hash(css_content + js_content)
    
    return AssetBundle(
        css=css_content,
        js=js_content,
        css_hash=css_hash,
        js_hash=js_hash,
        combined_hash=combined_hash,
    )


def get_css_bundle() -> str:
    """Get the concatenated CSS bundle."""
    return get_asset_bundle().css


def get_js_bundle() -> str:
    """Get the concatenated JS bundle."""
    return get_asset_bundle().js


def get_bundle_hash() -> str:
    """Get the combined hash for cache busting."""
    return get_asset_bundle().combined_hash


def invalidate_cache() -> None:
    """Clear the cached bundle (for development/testing)."""
    get_asset_bundle.cache_clear()
