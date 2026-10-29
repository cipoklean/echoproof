"""Turn spoken English numbers into digits so expected and heard values can be compared."""
from __future__ import annotations
import re

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
UNITS["oh"] = 0
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
NUMWORDS = set(UNITS) | set(TENS) | set(SCALES) | {"and", "point"}


def _words_to_number(words: list[str]) -> str:
    # Digit-by-digit runs ("nine eight seven six") -> "9876"
    if all(w in UNITS and UNITS[w] < 10 for w in words) and len(words) > 1:
        return "".join(str(UNITS[w]) for w in words)
    if "point" in words:
        i = words.index("point")
        whole = _words_to_number(words[:i]) if words[:i] else "0"
        frac = "".join(str(UNITS[w]) for w in words[i + 1:] if w in UNITS)
        return f"{whole}.{frac}"
    total, cur = 0, 0
    for w in words:
        if w == "and":
            continue
        if w in UNITS:
            cur += UNITS[w]
        elif w in TENS:
            cur += TENS[w]
        elif w == "hundred":
            cur *= 100
        elif w in SCALES:
            total += max(cur, 1) * SCALES[w]
            cur = 0
    return str(total + cur)


def canon(text: str) -> str:
    """Lowercase, numbers to digits, drop separators inside numbers, strip punctuation."""
    t = text.lower().replace("-", " ")
    t = re.sub(r"(?<=\d)[,\s](?=\d{3}\b)", "", t)  # 1,500 -> 1500
    t = re.sub(r"[^\w\s.]", " ", t)
    t = re.sub(r"\.(?!\d)", " ", t)
    toks = t.split()
    out, run = [], []
    for tok in toks + [""]:
        if tok in NUMWORDS and not (tok == "and" and not run):
            run.append(tok)
            continue
        if run:
            while run and run[-1] == "and":
                run.pop()
            out.append(_words_to_number(run))
            run = []
        if tok:
            out.append(tok)
    s = " ".join(out)
    # glue adjacent digit groups ("0 0 9 0" / "9 8 7 6")
    s = re.sub(r"\b(\d)(?: (?=\d\b)|(?=\b))", r"\1", s)
    return re.sub(r"(?<=\d) (?=\d)", "", s)
