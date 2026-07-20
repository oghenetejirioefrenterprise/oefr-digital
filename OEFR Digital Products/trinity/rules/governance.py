"""Governance gates for opportunities and LLM outputs.

This is the layer that prevents Trinity's agent loop from rationalizing
back to TJ's profession (the historical default failure). The model can
agree in prompt and then drift; this code does not drift.

Two checks:
  - check_opportunity(text): evaluates a proposed opportunity for
    edge fit and signal evidence.
  - check_llm_output(text, cycle): evaluates the output of morpheus,
    oracle, needle, product-loop for the networking-default pattern.

Both return GovernanceResult with pass/fail + reason. The calling
cycle decides whether to retry, escalate, or proceed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Markers we count as "signal evidence" in LLM text.
# When an opportunity or proposed product is in a TJ-default niche, we
# require the LLM output to cite at least N of these markers, otherwise
# we reject and force a retry.

_SIGNAL_MARKERS = [
    r"\bsearch\s+volume\b",
    r"\bgoogle\s+trends\b",
    r"\bkeyword\b",
    r"\bsubreddit\b",
    r"\br/[a-zA-Z0-9_]+",
    r"\bbestseller\b",
    r"\b\d+\s*(?:reviews?|sales?|customers?|members?|subscribers?)\b",
    r"\bmonthly\s+(?:searches|volume)\b",
    r"\bcompetitor[s]?\s+(?:on|with|charging)\b",
    r"\bvalidated\b",
    r"\blanding\s+page\s+test\b",
    r"\bpre[-\s]?(?:sale|order)\b",
    r"\bconversion\s+rate\b",
    r"\bhttps?://[^\s)]+",  # any URL counts as a citation
]

# Words/phrases that flag TJ-default networking-niche proposals.
NETWORKING_KEYWORDS = [
    r"\bnetwork\s+(?:engineer|admin|architect|architecture)\b",
    r"\bccna\b", r"\bccnp\b", r"\bccie\b",
    r"\bcomptia\b", r"\bnet\+\b",
    r"\bnetwork\s+troubleshoot",
    r"\brouter[s]?\b", r"\bswitch(?:es|ing)?\b",
    r"\bcisco\b", r"\bjuniper\b", r"\bpalo\s*alto\b",
    r"\bnetworking\s+(?:cert|certification|professional)",
    r"\bn8n\s+network",
    r"\bibkr\b", r"\binteractive\s+brokers\b",
]

REQUIRED_SIGNAL_COUNT = 3

# Non-edge markers — when an output proposes a market we know we can't win,
# we flag it regardless of signal. These mirror edges.md non-edges:
# brand trust, community embeddedness, taste in subcultures, personality.
NON_EDGE_MARKERS = [
    # Taste/community-driven Etsy subniches
    r"\bhandmade(?:[-\s]\w+)?\b",
    r"\bwedding\s+(?:planner|invitation|decor|template|stationery|favor)",
    r"\bhomeschool(?:\s+\w+)?\s+(?:planner|template|curriculum)",
    r"\bpostpartum\b",
    r"\bcrafting?\s+(?:template|bundle|kit)",
    r"\baesthetic\s+\w*(?:planner|template|design|wedding|pack)",
    # Personality-driven distribution
    r"\binstagram\s+(?:influencer|story|reels|persona)\b",
    r"\btiktok\s+(?:viral|influencer|persona|creator)\b",
    r"\bface[-\s]on[-\s]camera\b",
    r"\bcreator\s+persona\b",
    # Brand-required markets
    r"\bbrand\s+(?:trust|loyalty|recognition|equity)\b",
    r"\bpremium\s+positioning\b",
    # Sales-motion-required markets
    r"\benterprise\s+(?:sales|saas)\b",
    r"\bphone\s+(?:sales|outreach)\b",
    r"\bsales\s+(?:demo|call|motion)\b",
]


@dataclass
class GovernanceResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    signal_count: int = 0

    def as_text(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"Governance: {status}"]
        if self.reasons:
            lines.append("Reasons:")
            for r in self.reasons:
                lines.append(f"  - {r}")
        if self.flags:
            lines.append("Flags:")
            for f in self.flags:
                lines.append(f"  - {f}")
        lines.append(f"Signal markers found: {self.signal_count}")
        return "\n".join(lines)


# ── Helpers ─────────────────────────────────────────────────────

def _count_signal_markers(text: str) -> int:
    text_l = text.lower()
    return sum(1 for pat in _SIGNAL_MARKERS if re.search(pat, text_l))


def _matches_any(text: str, patterns: list[str]) -> list[str]:
    text_l = text.lower()
    matched = []
    for pat in patterns:
        if re.search(pat, text_l):
            matched.append(pat)
    return matched


# Filenames and filesystem paths must not trip niche keywords
# (e.g. "deploy-lane-router.py" matching \brouter\b — 2 live false
# positives 07-09/07-10, each costing a full cycle). URLs are left
# intact: they are signal markers, and r/sub references stay too.
_PATH_TOKEN_RE = re.compile(
    r"(?<!\S)"                      # token start
    r"(?!https?://)(?!r/)"          # keep URLs and r/subreddits
    r"(?:~?/?[\w.+-]+(?:/[\w.+-]+)+/?"       # slash paths: a/b, ~/x/y.py
    r"|[\w+-]*[\w+-]\.(?:py|sh|js|ts|jsx|tsx|json|md|ya?ml|txt|log|csv|toml|cfg|ini)"  # bare filenames
    r")(?![\w+/-])",  # end at whitespace or punctuation (.py, / .py) — not mid-token
    re.IGNORECASE,
)


# Known workspace script stems that agents reference WITHOUT an
# extension (e.g. "deploy-lane-router 0/0/0"). Hyphenated compounds —
# never a product proposal.
_SCRIPT_STEM_RE = re.compile(
    r"(?<!\S)(?:deploy-lane-router|lane-router|lane-triage)[s]?\b:?"
    # "Router:" / "**Router:**" section labels (echo the script) — not a proposal.
    # (?<![\w/-]) instead of (?<!\S) so markdown bold/underscore prefixes pass;
    # bare colon (no (?=\s)) so "Router:**" closes too. 4th live FP 2026-07-20.
    r"|(?<![\w/-])router\b:"
    # "Router first: ..." section phrasing (validator-executor output style)
    r"|(?<![\w/-])router\s+first\b:?",
    re.IGNORECASE,
)


def _strip_path_tokens(text: str) -> str:
    """Remove file paths/filenames before niche-keyword matching only.

    Never applied to signal counting — URLs must keep counting there.
    """
    return _SCRIPT_STEM_RE.sub(" ", _PATH_TOKEN_RE.sub(" ", text))


# ── Public checks ───────────────────────────────────────────────

def check_opportunity(text: str) -> GovernanceResult:
    """Evaluate a proposed opportunity (typically from opportunity-scout).

    Phase 0: same logic as check_llm_output. Phase 2 will add
    edge-match scoring against edges.md and validation-record gating.
    """
    return check_llm_output(text, cycle="opportunity-scout")


def check_llm_output(text: str, cycle: str = "") -> GovernanceResult:
    """Evaluate an LLM cycle output for governance compliance.

    Rejects (passed=False) when:
      - Output proposes a networking-niche product/opportunity AND
        cites fewer than REQUIRED_SIGNAL_COUNT signal markers.
      - Output proposes a non-edge market (Etsy handmade, Instagram
        influencer, etc.) regardless of signal count.

    Pass with flags when:
      - Output proposes a networking niche WITH sufficient signal
        evidence (caller may still want to review).
      - Output is signal-light but doesn't propose a flagged niche.
    """
    result = GovernanceResult(passed=True)

    # Niche/non-edge matching runs on path-stripped text so script
    # filenames (deploy-lane-router.py) can't trip \brouter\b etc.
    # Signal counting stays on the FULL text — URLs are signals.
    keyword_text = _strip_path_tokens(text)
    network_hits = _matches_any(keyword_text, NETWORKING_KEYWORDS)
    non_edge_hits = _matches_any(keyword_text, NON_EDGE_MARKERS)
    signal_count = _count_signal_markers(text)
    result.signal_count = signal_count

    if non_edge_hits:
        result.passed = False
        result.reasons.append(
            f"Output proposes non-edge market(s): {', '.join(non_edge_hits)}. "
            f"See edges.md — these markets reward edges OEFR doesn't have."
        )

    if network_hits:
        if signal_count < REQUIRED_SIGNAL_COUNT:
            result.passed = False
            result.reasons.append(
                f"Output proposes networking-niche content ({len(network_hits)} matches: "
                f"{', '.join(network_hits[:3])}{'...' if len(network_hits) > 3 else ''}) "
                f"but only cites {signal_count}/{REQUIRED_SIGNAL_COUNT} signal markers. "
                f"TJ-default niche requires ≥{REQUIRED_SIGNAL_COUNT} demand-signal citations "
                f"(search volume, keyword data, competitor sales, validated tests, URLs to evidence). "
                f"Retry with explicit market evidence or pick a different opportunity."
            )
        else:
            result.flags.append(
                f"Networking-niche proposal passed signal threshold ({signal_count} markers); "
                f"governance allows but logs for override review."
            )

    if result.passed and not result.flags and not network_hits and not non_edge_hits:
        result.reasons.append("No governance flags raised.")

    return result


def retry_instruction(result: GovernanceResult, cycle: str) -> str:
    """Generate the retry prompt suffix when governance fails.

    Used by cron_runner.py to prepend a stronger constraint to the
    next agent invocation.
    """
    lines = [
        "",
        "## Governance feedback on previous attempt",
        f"Your previous output was rejected by governance ({cycle}).",
        "",
        *(f"- {r}" for r in result.reasons),
        "",
        "Required for this retry:",
        "1. Do NOT propose networking/cisco/CCNA/CCNP/router/switch products unless you cite at least 3 specific demand signals (Google Trends data, keyword search volume, subreddit member counts, competitor sales counts, URLs to evidence, or pre-sale validation results).",
        "2. Do NOT propose markets requiring brand, community embeddedness, or personality (Etsy handmade aesthetic, Instagram influencer plays, enterprise sales motion). See knowledge/edges.md.",
        "3. Prefer markets that reward OEFR's actual edges: speed, AI cost structure, parallel experimentation, willingness to kill fast.",
        "4. Cite specific evidence with URLs or numbers, not general claims.",
    ]
    return "\n".join(lines)
