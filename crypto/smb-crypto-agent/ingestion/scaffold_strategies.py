"""
Phase-3: scaffold strategies/<slug>/ directories for every high/med-confidence
setup found in knowledge_base/setups/.

Reads each setup markdown file, parses the header line containing
`**Category:** X  **Timeframe:** Y  **Confidence:** Z  **Venues:** ...`,
and creates a strategy dir with detector stub + playbook copy + bot stub.
"""
import re
import shutil
from pathlib import Path


SETUP_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base" / "setups"
STRATEGIES_ROOT = Path(__file__).resolve().parent.parent / "strategies"

HEADER_RE = re.compile(
    r"\*\*Category:\*\*\s*(?P<category>[\w_]+)\s+"
    r"\*\*Timeframe:\*\*\s*(?P<timeframe>\w+)\s+"
    r"\*\*Confidence:\*\*\s*(?P<confidence>\w+)\s+"
    r"\*\*Venues:\*\*\s*(?P<venues>.+)"
)


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "_")


def parse_header(text: str) -> dict[str, str] | None:
    for line in text.splitlines():
        m = HEADER_RE.search(line)
        if m:
            return m.groupdict()
    return None


def scaffold_one(setup_md: Path) -> Path | None:
    text = setup_md.read_text(encoding="utf-8")
    header = parse_header(text)
    if not header:
        return None
    if header["confidence"].lower() not in {"high", "med"}:
        return None
    slug = slugify(setup_md)
    dest = STRATEGIES_ROOT / slug
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(setup_md, dest / "playbook.md")
    (dest / "detector.py").write_text(_detector_stub(slug, header), encoding="utf-8")
    (dest / "bot.py").write_text(_bot_stub(slug), encoding="utf-8")
    (dest / "__init__.py").write_text("", encoding="utf-8")
    return dest


def _detector_stub(slug: str, header: dict[str, str]) -> str:
    return f'''"""
Detector for {slug}.
Category: {header['category']}   Timeframe: {header['timeframe']}   Confidence: {header['confidence']}
Venues: {header['venues']}

NOT IMPLEMENTED. Implement `find_candidates` so it emits dict candidates consumed by
`core/judge.py`. See playbook.md in this directory for the distilled rules.
"""
from dataclasses import dataclass


@dataclass
class Candidate:
    symbol: str
    venue: str
    direction: str
    setup: str
    features: dict


def find_candidates(market_ctx) -> list[Candidate]:
    raise NotImplementedError("implement detector from playbook.md")
'''


def _bot_stub(slug: str) -> str:
    return f'''"""
Runner for {slug}. Wires detector -> risk -> judge -> allocator -> venue.
Implementation arrives in Plan 2/3.
"""


def run_once():
    raise NotImplementedError
'''


def scaffold_all() -> list[Path]:
    created: list[Path] = []
    for md in sorted(SETUP_ROOT.glob("*.md")):
        dest = scaffold_one(md)
        if dest:
            created.append(dest)
    return created


if __name__ == "__main__":
    for d in scaffold_all():
        print(f"scaffolded {d}")
