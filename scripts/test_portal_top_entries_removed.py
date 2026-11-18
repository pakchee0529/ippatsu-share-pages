"""Check the generated template and the TOP HTML proposed for publication."""

from pathlib import Path
import sys

from generate_portal import build_html


def check_public_top(page: str, source: str) -> None:
    for removed in (
        "weekly-plan",
        "print-test-entry",
        "print-260721",
        "./weekly/2026-11-02.pdf",
        "ojt-intake-heading",
        "feedback-intake-heading",
        'class="intro"',
    ):
        assert removed not in page, f"{source}: unexpected TOP entry {removed}"
    for retained in ("theme: Furrow", "today-schedule-root", "./calendar/"):
        assert retained in page, f"{source}: missing approved format or link {retained}"
    assert page.index("today-schedule-heading") < page.index('class="card-list"'), source


if __name__ == "__main__":
    fixture = build_html([("261104", "2026年11月04日")], calendar_api_key="")
    check_public_top(fixture, "generator output")
    assert "../share/261104/" in fixture
    default = Path(__file__).resolve().parents[1] / "portal" / "index.html"
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    check_public_top(target.read_text(encoding="utf-8-sig"), str(target))
    print("PASS: generated and publishable TOP retain the approved format and entries")
