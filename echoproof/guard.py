"""Pre-speech guard: find and neutralise text tricks before it reaches TTS."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Bidi controls and invisible format characters
BIDI = {"\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069", "\u200e", "\u200f"}
INVISIBLE = {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad", "\u180e"}

# Common look-alikes (Cyrillic / Greek) mapped to Latin
CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    "ο": "o", "α": "a", "ν": "v", "ρ": "p", "Ο": "O", "Α": "A", "Β": "B", "Ε": "E", "Ι": "I", "Κ": "K", "Ν": "N", "Τ": "T",
}


@dataclass
class Finding:
    kind: str
    char: str
    index: int
    detail: str


@dataclass
class GuardResult:
    original: str
    cleaned: str
    displayed: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def tampered(self) -> bool:
        return bool(self.findings)


def _script(ch: str) -> str:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return "UNKNOWN"
    return name.split(" ")[0]


def visual_order(text: str) -> str:
    """Approximate what a screen shows for RLO/LRO/PDF runs (enough for the attack demo)."""
    out: list[str] = []
    stack: list[list[str]] = []
    for ch in text:
        if ch in ("\u202e", "\u2067"):  # RLO, RLI
            stack.append([])
        elif ch in ("\u202c", "\u2069") and stack:  # PDF, PDI
            run = stack.pop()
            target = stack[-1] if stack else out
            target.extend(reversed(run))
        elif ch in BIDI or ch in INVISIBLE or 0xE0000 <= ord(ch) <= 0xE007F or 0xFE00 <= ord(ch) <= 0xFE0F:
            continue
        else:
            (stack[-1] if stack else out).append(ch)
    while stack:
        run = stack.pop()
        (stack[-1] if stack else out).extend(reversed(run))
    return "".join(out)


def guard(text: str) -> GuardResult:
    findings: list[Finding] = []
    for i, ch in enumerate(text):
        if ch in BIDI:
            findings.append(Finding("bidi_control", f"U+{ord(ch):04X}", i, "can make the screen show a different order than the voice reads"))
        elif ch in INVISIBLE:
            findings.append(Finding("invisible", f"U+{ord(ch):04X}", i, "hidden character"))
        elif ch in CONFUSABLES:
            findings.append(Finding("homoglyph", ch, i, f"{_script(ch).title()} letter that looks like '{CONFUSABLES[ch]}'"))
        elif 0xE0000 <= ord(ch) <= 0xE007F:
            findings.append(Finding("tag_char", f"U+{ord(ch):04X}", i, "invisible tag character (ASCII smuggling)"))
        elif 0xFE00 <= ord(ch) <= 0xFE0F or 0xE0100 <= ord(ch) <= 0xE01EF:
            findings.append(Finding("variation_selector", f"U+{ord(ch):04X}", i, "invisible variation selector"))
        elif unicodedata.category(ch) == "Mn" and i and text[i-1].isdigit():
            findings.append(Finding("combining_on_digit", f"U+{ord(ch):04X}", i, "mark stacked on a digit"))
        elif unicodedata.decomposition(ch).split(" ")[0] in ("<wide>", "<font>", "<super>", "<sub>", "<circle>", "<fraction>"):
            findings.append(Finding("compat_form", ch, i, f"styled form of '{unicodedata.normalize('NFKC', ch)}'"))
        elif ch.isdigit() and not ch.isascii():
            findings.append(Finding("foreign_digit", ch, i, f"{_script(ch).title()} digit {unicodedata.digit(ch, '?')}"))
    displayed = visual_order(text)
    cleaned = "".join(ch for ch in displayed)  # speak what the user sees
    cleaned = "".join(CONFUSABLES.get(ch, ch) for ch in cleaned)
    # keep meaning that NFKC would destroy: 10² is "10 squared", not "102"
    cleaned = re.sub("[⁰¹²³⁴-⁹]+", lambda m: " to the power of " + unicodedata.normalize("NFKC", m.group()), cleaned)
    cleaned = unicodedata.normalize("NFKC", cleaned).replace("⁄", "/")
    cleaned = "".join(str(unicodedata.digit(c)) if c.isdigit() and not c.isascii() else c for c in cleaned)
    cleaned = "".join(c for i, c in enumerate(cleaned) if not (unicodedata.category(c) == "Mn" and i and cleaned[i-1].isdigit()))
    return GuardResult(original=text, cleaned=cleaned, displayed=displayed, findings=findings)
