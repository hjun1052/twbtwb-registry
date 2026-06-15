#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
RAW_PREFIX = "https://raw.githubusercontent.com/hjun1052/twbtwb-registry/main/"
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
}


def fail(message: str) -> None:
    print(f"registry validation failed: {message}", file=sys.stderr)
    sys.exit(1)


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except Exception as exc:
        fail(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must be a JSON object")
    return value


def require_string(obj: dict, field: str, path: Path) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        fail(f"{path.relative_to(ROOT)} missing non-empty string field {field}")
    return value.strip()


def require_version(obj: dict, path: Path) -> None:
    if obj.get("version") != 1:
        fail(f"{path.relative_to(ROOT)} must set version to 1")


def require_name(value: str, path: Path, field: str = "name") -> None:
    if not NAME_RE.fullmatch(value):
        fail(f"{path.relative_to(ROOT)} has invalid {field}: {value}")


def require_https_url(value: str, path: Path, field: str = "url") -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https":
        fail(f"{path.relative_to(ROOT)} {field} must be https://: {value}")
    host = parsed.hostname or ""
    if host.lower() in BLOCKED_HOSTS:
        fail(f"{path.relative_to(ROOT)} {field} must not point to local host: {value}")
    if host.endswith(".local"):
        fail(f"{path.relative_to(ROOT)} {field} must not point to .local host: {value}")


def validate_big_registry() -> set[Path]:
    path = ROOT / "big-registry.json"
    data = load_json(path)
    require_version(data, path)
    registries = data.get("registries")
    if not isinstance(registries, list) or not registries:
        fail("big-registry.json must contain a non-empty registries array")

    referenced = set()
    seen_names = set()
    for index, registry in enumerate(registries):
        if not isinstance(registry, dict):
            fail(f"big-registry.json registries[{index}] must be an object")
        name = require_string(registry, "name", path)
        require_name(name, path)
        if name in seen_names:
            fail(f"duplicate registry name: {name}")
        seen_names.add(name)
        require_string(registry, "title", path)
        url = require_string(registry, "url", path)
        require_https_url(url, path)
        if not url.startswith(RAW_PREFIX):
            fail(f"registry URL must use this repo raw main URL: {url}")
        local = ROOT / url.removeprefix(RAW_PREFIX)
        if not local.exists():
            fail(f"registry URL points to missing local file: {local.relative_to(ROOT)}")
        referenced.add(local.resolve())

    return referenced


def validate_registry_file(path: Path) -> None:
    data = load_json(path)
    require_version(data, path)
    name = require_string(data, "name", path)
    require_name(name, path)
    require_string(data, "title", path)
    sites = data.get("sites")
    if not isinstance(sites, list):
        fail(f"{path.relative_to(ROOT)} must contain a sites array")

    seen_names = set()
    for index, site in enumerate(sites):
        if not isinstance(site, dict):
            fail(f"{path.relative_to(ROOT)} sites[{index}] must be an object")
        site_name = require_string(site, "name", path)
        require_name(site_name, path, "site name")
        if site_name in seen_names:
            fail(f"{path.relative_to(ROOT)} duplicates site name: {site_name}")
        seen_names.add(site_name)
        require_string(site, "title", path)
        require_https_url(require_string(site, "url", path), path, "site url")
        if "description" in site and not isinstance(site["description"], str):
            fail(f"{path.relative_to(ROOT)} site description must be a string")
        tags = site.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            fail(f"{path.relative_to(ROOT)} site tags must be a string array")


def main() -> None:
    referenced = validate_big_registry()
    registry_files = set((ROOT / "registries").glob("*.json"))
    if not registry_files:
        fail("registries/ must contain at least one JSON registry")
    for path in sorted(registry_files):
        validate_registry_file(path)
    unreferenced = {path.resolve() for path in registry_files} - referenced
    if unreferenced:
        names = ", ".join(str(path.relative_to(ROOT)) for path in sorted(unreferenced))
        fail(f"registry files are not referenced by big-registry.json: {names}")
    print(f"validated {1 + len(registry_files)} registry JSON files")


if __name__ == "__main__":
    main()
