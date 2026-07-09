"""Verify generated completion archive pages.

This is a read-only pre-publish guard for portal/archive HTML. It checks the
invariants that have bitten us in production: archive TOP labels, detail card
counts, planned-incomplete sections, and map availability when coordinates
exist in the completion export.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


UNKNOWN_LABEL = "現場名未取得"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm_spaces(value: str) -> str:
    return " ".join(value.split())


def _strip_card_suffix(value: str) -> str:
    value = _norm_spaces(value)
    for suffix in (" 完了", " 未完了"):
        if value.endswith(suffix):
            return value[: -len(suffix)].strip()
    return value


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _export_json_path(export_root: Path, date_key: str) -> Path:
    return export_root / f"{date_key}.json"


def _item_label(item: dict[str, Any]) -> str:
    src = item.get("source_item")
    if isinstance(src, dict):
        label = _text(src.get("label"))
        if label:
            return label
    return _text(item.get("label"))


def _has_latlng_in_source(item: dict[str, Any]) -> bool:
    src = item.get("source_item")
    if not isinstance(src, dict):
        return False
    for lat_key, lng_key in (
        ("lat", "lng"),
        ("start_lat", "start_lng"),
        ("end_lat", "end_lng"),
    ):
        try:
            lat = float(src.get(lat_key))
            lng = float(src.get(lng_key))
        except (TypeError, ValueError):
            continue
        if lat != 0.0 and lng != 0.0:
            return True
    return bool(_text(src.get("map_url")))


@dataclass
class ArchiveTopRow:
    date_key: str = ""
    main: str = ""
    count: str = ""
    href: str = ""
    search: str = ""


class ArchiveTopParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[ArchiveTopRow] = []
        self._row: ArchiveTopRow | None = None
        self._depth = 0
        self._capture: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        classes = set(attr.get("class", "").split())
        if tag == "article" and "archive-row" in classes:
            self._row = ArchiveTopRow(search=attr.get("data-search", ""))
            self._depth = 1
            return
        if not self._row:
            return
        self._depth += 1
        if tag == "a" and "btn-archive" in classes:
            self._row.href = attr.get("href", "")
        if "archive-main" in classes:
            self._start_capture("main")
        elif "archive-count" in classes:
            self._start_capture("count")
        elif "archive-dkey" in classes:
            self._start_capture("date")

    def handle_endtag(self, tag: str) -> None:
        if self._capture and self._row:
            value = _norm_spaces("".join(self._buf))
            if self._capture == "main":
                self._row.main = value
            elif self._capture == "count":
                self._row.count = value
            elif self._capture == "date":
                self._row.date_key = value.strip("()")
            self._capture = None
            self._buf = []
        if self._row:
            self._depth -= 1
            if self._depth == 0:
                self.rows.append(self._row)
                self._row = None

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buf.append(data)

    def _start_capture(self, name: str) -> None:
        self._capture = name
        self._buf = []


@dataclass
class ArchiveDetailInfo:
    card_titles: list[str] = field(default_factory=list)
    planned_cards: int = 0
    has_map: bool = False
    map_empty: bool = False
    points_count: int = 0


class ArchiveDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.info = ArchiveDetailInfo()
        self._capture_title = False
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        classes = set(attr.get("class", "").split())
        if tag == "article" and "card-planned-incomplete" in classes:
            self.info.planned_cards += 1
        if tag == "h2" and "card-title" in classes:
            self._capture_title = True
            self._buf = []
        if attr.get("id") == "share-map":
            self.info.has_map = True
        if "map-empty" in classes:
            self.info.map_empty = True

    def handle_endtag(self, tag: str) -> None:
        if self._capture_title and tag == "h2":
            self.info.card_titles.append(_strip_card_suffix("".join(self._buf)))
            self._capture_title = False
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._buf.append(data)


def parse_archive_top(path: Path) -> list[ArchiveTopRow]:
    parser = ArchiveTopParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.rows


def parse_archive_detail(path: Path) -> ArchiveDetailInfo:
    html = path.read_text(encoding="utf-8", errors="replace")
    parser = ArchiveDetailParser()
    parser.feed(html)
    match = re.search(r"var points = (\[.*?\]);", html, flags=re.S)
    if match:
        try:
            points = json.loads(match.group(1))
            if isinstance(points, list):
                parser.info.points_count = len(points)
        except json.JSONDecodeError:
            parser.info.points_count = -1
    return parser.info


def expected_labels(export: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for group in ("items", "planned_but_incomplete"):
        arr = export.get(group)
        if not isinstance(arr, list):
            continue
        for item in arr:
            if isinstance(item, dict):
                label = _item_label(item)
                if label:
                    labels.append(label)
    return labels


def expected_counts(export: dict[str, Any]) -> tuple[int, int]:
    items = export.get("items")
    planned = export.get("planned_but_incomplete")
    return (
        len(items) if isinstance(items, list) else 0,
        len(planned) if isinstance(planned, list) else 0,
    )


def expected_point_count(export: dict[str, Any]) -> int:
    count = 0
    for group in ("items", "planned_but_incomplete"):
        arr = export.get(group)
        if not isinstance(arr, list):
            continue
        for item in arr:
            if isinstance(item, dict) and _has_latlng_in_source(item):
                count += 1
    return count


def verify(repo_root: Path, export_root: Path | None, dates: set[str] | None) -> list[str]:
    failures: list[str] = []
    archive_root = repo_root / "portal" / "archive"
    top_path = archive_root / "index.html"
    manifest_path = archive_root.parent / "archive_manifest.json"
    if not top_path.is_file():
        return [f"missing {top_path}"]
    if not manifest_path.is_file():
        return [f"missing {manifest_path}"]

    manifest = _load_json(manifest_path)
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return ["portal/archive_manifest.json entries must be a list"]

    rows = parse_archive_top(top_path)
    rows_by_date = {row.date_key: row for row in rows if row.date_key}
    if len(rows_by_date) != len(rows):
        failures.append("archive TOP has row(s) without date key")

    for row in rows:
        if not row.main or row.main == "—":
            failures.append(f"archive TOP {row.date_key or '?'} has blank title")
        if row.href and row.date_key and row.date_key not in row.href:
            failures.append(f"archive TOP {row.date_key} href mismatch: {row.href}")

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            failures.append("archive manifest contains non-object entry")
            continue
        date_key = _text(raw_entry.get("date"))
        if not date_key or (dates and date_key not in dates):
            continue
        href = _text(raw_entry.get("href"))
        expected_href = f"./{date_key}/"
        if href != expected_href:
            failures.append(
                f"archive manifest {date_key} href must be {expected_href}: {href or '(blank)'}"
            )
        row = rows_by_date.get(date_key)
        if not row:
            failures.append(f"archive TOP missing manifest date {date_key}")
            continue

        detail_path = archive_root / date_key / "index.html"
        if not detail_path.is_file():
            failures.append(f"archive detail missing for {date_key}")
            continue
        detail = parse_archive_detail(detail_path)

        export: dict[str, Any] | None = None
        if export_root:
            export_path = _export_json_path(export_root, date_key)
            if export_path.is_file():
                export = _load_json(export_path)

        if export:
            item_count, planned_count = expected_counts(export)
            labels = expected_labels(export)
            if labels and row.main == UNKNOWN_LABEL:
                failures.append(f"archive TOP {date_key} used unknown label despite export labels")
            for label in labels[:4]:
                if label and label not in row.search:
                    failures.append(f"archive TOP {date_key} search missing label: {label}")
            if item_count + planned_count > 0 and len(detail.card_titles) < item_count + planned_count:
                failures.append(
                    f"archive detail {date_key} cards {len(detail.card_titles)} "
                    f"< export total {item_count + planned_count}"
                )
            if detail.planned_cards != planned_count:
                failures.append(
                    f"archive detail {date_key} planned cards {detail.planned_cards} "
                    f"!= export planned {planned_count}"
                )
            points_expected = expected_point_count(export)
            if points_expected > 0:
                if not detail.has_map or detail.map_empty:
                    failures.append(f"archive detail {date_key} missing map despite coordinates")
                if detail.points_count < points_expected:
                    failures.append(
                        f"archive detail {date_key} map points {detail.points_count} "
                        f"< expected {points_expected}"
                    )
        elif row.main == "—":
            failures.append(f"archive TOP {date_key} still uses dash fallback")

    return failures


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="ippatsu-share-pages root (default: script parent)",
    )
    parser.add_argument(
        "--completion-reports-root",
        type=Path,
        default=None,
        help="Optional export root containing YYMMDD.json files.",
    )
    parser.add_argument(
        "--date",
        action="append",
        default=[],
        help="Limit verification to one YYMMDD date. Repeatable.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(list(argv or sys.argv[1:]))
    repo_root = ns.repo_root.resolve()
    export_root = ns.completion_reports_root.resolve() if ns.completion_reports_root else None
    dates = set(ns.date) if ns.date else None
    failures = verify(repo_root, export_root, dates)
    if failures:
        print("archive verification: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    scope = ", ".join(sorted(dates)) if dates else "all manifest dates"
    print(f"archive verification: OK ({scope})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
