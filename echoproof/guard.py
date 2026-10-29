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


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
# English locales that write day first. TTS-1 reads English slash dates month-first
# (US); other TTS-1 languages already read them day-first.
DAY_FIRST_EN = {"en-gb", "en-ng", "en-ie", "en-au", "en-nz", "en-in", "en-za", "en-ke", "en-gh"}
DATE = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")


def _dates(text: str, locale: str, findings: list) -> str:
    """Spell out slash dates in English so the voice can't pick the wrong order."""
    loc = locale.lower()
    if not loc.startswith("en"):
        return text
    day_first = loc in DAY_FIRST_EN

    def fix(m):
        a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
        d, mo = (a, b) if day_first else (b, a)
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            return m.group()
        if a <= 12 and b <= 12 and a != b:
            findings.append(Finding("ambiguous_date", m.group(), m.start(),
                                    f"reads as {MONTHS[mo-1]} {d} in {locale}, {MONTHS[a-1 if day_first else b-1]} {b if day_first else a} elsewhere"))
        return f"{d} {MONTHS[mo-1]} {y}" if day_first else f"{MONTHS[mo-1]} {d}, {y}"

    return DATE.sub(fix, text)


# words used to read "1500 euro AND 50 cents" / "2 COMMA 5 mg" per language
_AND = {"de": ("und", "Cent", "Komma"), "it": ("e", "centesimi", "virgola"), "es": ("con", "céntimos", "coma"),
        "fr": ("et", "centimes", "virgule"), "pt": ("e", "centavos", "vírgula")}
_CUR_WORD = {"€": {"de": "Euro", "it": "euro", "es": "euros", "fr": "euros", "pt": "euros"}, "R$": {"pt": "reais"}}
_MONEY_EU = re.compile(r"(R\$\s?)?(\d{1,3}(?:[.\u00a0 ]\d{3})+|\d+),(\d{2})(?!\d)\s*(€|Euro|euros?|EUR)?")
_DEC_UNIT = re.compile(r"(\d+),(\d+)\s*(mg|ml|mL|g|mcg|µg)\b")
_UNIT_WORD = {"mg": "mg", "ml": "ml", "mL": "ml", "g": "g", "mcg": "µg", "µg": "µg"}
# Indian grouping: 1,50,000 / 12,34,56,789
_LAKH = re.compile(r"(₹|Rs\.?\s?|INR\s?)(\d{1,2}(?:,\d{2})+,\d{3})(?!\d)")


def _numbers(text: str, locale: str, findings: list) -> str:
    """Rewrite separators that TTS-1 voices misread into an unambiguous spoken form."""
    def lakh(m):
        n = int(m.group(2).replace(",", ""))
        findings.append(Finding("indian_grouping", m.group(), m.start(), f"lakh/crore grouping = {n:,}"))
        return f"{n:,} rupees"
    text = _LAKH.sub(lakh, text)
    lang = locale.lower()[:2]
    if lang not in _AND:
        return text
    conj, cents, comma = _AND[lang]

    def money(m):
        prefix, whole, frac, cur = m.groups()
        # only "1.500,50": a dot that could be read as a decimal point. Measured:
        # French "1 500,50 €" reads fine raw, and rewriting it made aai-jane drop "euros".
        if (not prefix and not cur) or "." not in whole:
            return m.group()
        unit = _CUR_WORD["R$"][lang] if prefix and lang in _CUR_WORD["R$"] else _CUR_WORD["€"][lang]
        n = int(re.sub(r"\D", "", whole))
        findings.append(Finding("decimal_comma_money", m.group(), m.start(), f"{n} {unit} {conj} {int(frac)} {cents}"))
        return f"{n} {unit} {conj} {int(frac)} {cents}"

    def dose(m):
        findings.append(Finding("decimal_comma_dose", m.group(), m.start(), "decimal comma in a dose"))
        return f"{m.group(1)} {comma} {m.group(2)} {_UNIT_WORD[m.group(3)]}"

    return _DEC_UNIT.sub(dose, _MONEY_EU.sub(money, text))


BUILTIN_VOICES = {"aai-jane", "aai-alba", "aai-anna", "aai-charles", "aai-eve", "aai-george",
                  "aai-jean", "aai-mary", "aai-michael", "aai-paul", "aai-vera"}


def check_voice(voice: str, language: str) -> Finding | None:
    """Built-in voices speak other languages worse than English (AssemblyAI docs); measured:
    aai-jane garbles German words around numbers ("Nehmen Sie 2,5 mg" -> "Namen C2, 5 mg")."""
    if voice in BUILTIN_VOICES and language.lower() not in ("english", "en"):
        return Finding("voice_language", voice, 0, f"built-in voice speaking {language}; use a native {language} voice")
    return None


def guard(text: str, locale: str = "en-us") -> GuardResult:
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
    cleaned = _dates(cleaned, locale, findings)
    cleaned = _numbers(cleaned, locale, findings)
    return GuardResult(original=text, cleaned=cleaned, displayed=displayed, findings=findings)
