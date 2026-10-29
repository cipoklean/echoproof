"""Learn how to make TTS-1 say a name right.

TTS-1 has no pronunciation lexicon, so EchoProof searches respellings: each candidate
is spoken in a carrier sentence and transcribed by Sync STT *without* hints, and the
word in the name slot is checked against SOUNDS_RIGHT: spellings a transcriber writes
when it hears the correct pronunciation (e.g. Saoirse heard as "Sirsha" is correct).

Priming STT with the name as a keyterm is useless as a verifier: it returned the right
spelling for every raw name, including ones TTS-1 clearly mispronounced.

    python -m echoproof.names            # writes echoproof/lexicon.json
"""
from __future__ import annotations
import json, pathlib, re
from concurrent.futures import ThreadPoolExecutor
from .client import speak, transcribe

CARRIER = "Please welcome {} to the call."
VOICES = ["aai-audrey", "aai-jane"]

# name -> respelling candidates (English phonetics)
CANDIDATES = {
    "Aoife": ["Eefa", "Ee-fah", "EE-fuh"],
    "Saoirse": ["Seersha", "Seer-sha", "SEER-shuh"],
    "Siobhan": ["Shivawn", "Shi-vawn", "Shuh-vawn"],
    "Niamh": ["Neev", "Neeve", "Nee-iv"],
    "Xochitl": ["Socheel", "Sochil", "Soh-cheel", "So-cheetl"],
    "Nguyen": ["Win", "Nwin", "Ngwen"],
    "Chukwuemeka": ["Chook-weh-meh-ka", "Chuk-wu-eh-meh-ka", "Chookwemeka"],
    "Oluwaseun": ["Oluwashayun", "Oh-loo-wah-shay-oon", "Oluwa-shayoon", "Olu-wa-shay-un"],
    "Ngozi": ["N-go-zee", "Ngo-zee", "Inn-go-zee"],
    "Joaquín": ["Wah-keen", "Hwah-keen", "Wakeen"],
    "Siân": ["Shahn", "Sharn", "Shaan"],
    "Mbappé": ["Em-bah-pay", "Mbah-pay", "Um-bap-ay"],
}


# spellings an unprimed transcriber produces for a CORRECT pronunciation
SOUNDS_RIGHT = {
    "Aoife": ["aoife", "eefa", "efa", "ifa", "eefah", "eepha"],
    "Saoirse": ["saoirse", "sirsha", "seersha", "sirscha", "searsha", "sersha", "seersa"],
    "Siobhan": ["siobhan", "shivaun", "shivon", "shevonne", "chevonne", "shivawn", "shavon", "shivan"],
    "Niamh": ["niamh", "neve", "neev", "neave", "niev", "neeve"],
    "Xochitl": ["xochitl", "sochil", "socheel", "sochill", "sochee", "sochi", "soachil"],
    "Nguyen": ["nguyen", "win", "wynn", "nwin", "ngwin", "nwen", "ngwen", "when"],
    "Chukwuemeka": ["chukwuemeka", "chukwumeka", "chookwemeka"],
    "Oluwaseun": ["oluwaseun", "oluwashayun", "oluwasheun", "oluwashayoon"],
    "Ngozi": ["ngozi", "ingozi", "engozi"],
    "Joaquín": ["joaquin", "wakeen", "walkeen", "huakeen", "wahkeen"],
    "Siân": ["shan", "sharn", "shahn", "shaan", "sian"],
    "Mbappé": ["mbappe", "embappe", "mbape", "embape"],
}


# Heard by ear (Oct 29, 2026): TTS-1 says Nguyen as "Nuh-goo-yen" even though STT,
# which knows the name, still writes "Nguyen". Listening overrides the transcript.
BY_EAR = {"Nguyen": "Win"}


def _norm(w: str) -> str:
    import unicodedata
    w = unicodedata.normalize("NFKD", w)
    return re.sub(r"[^a-z]", "", "".join(c for c in w if not unicodedata.combining(c)).lower())


def slot(heard: str) -> str:
    m = re.search(r"welcome,?\s+(.*?)[,.]?\s+to the call", heard, re.I)
    return m.group(1) if m else heard


def _ok(name: str, heard: str) -> bool:
    return _norm(slot(heard)) in SOUNDS_RIGHT[name]


def trial(name: str, said: str, voice: str, keyterm: bool) -> dict:
    wav = speak(CARRIER.format(said), voice=voice)
    heard = transcribe(wav, "en", [name] if keyterm else None).get("text", "")
    return {"name": name, "said": said, "voice": voice, "keyterm": keyterm, "heard": heard, "pass": _ok(name, heard)}


def learn() -> dict:
    jobs = []
    for name, cands in CANDIDATES.items():
        for v in VOICES:
            jobs += [(name, name, v, False), (name, name, v, True)]
            jobs += [(name, c, v, False) for c in cands]
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(lambda j: trial(*j), jobs))
    lex, summary = {}, []
    for name, cands in CANDIDATES.items():
        r = [x for x in rows if x["name"] == name]
        raw_plain = sum(x["pass"] for x in r if x["said"] == name and not x["keyterm"])
        raw_kt = sum(x["pass"] for x in r if x["said"] == name and x["keyterm"])
        best = None
        for c in cands:  # first candidate that works on every voice
            if all(x["pass"] for x in r if x["said"] == c):
                best = c
                break
        if best and raw_plain < len(VOICES):
            lex[name] = best
        summary.append({"name": name, "raw_plain": f"{raw_plain}/{len(VOICES)}", "raw_keyterm": f"{raw_kt}/{len(VOICES)}",
                        "respelling": best, "heard_raw": [slot(x["heard"]) for x in r if x["said"] == name and not x["keyterm"]],
                        "heard_respelled": [slot(x["heard"]) for x in r if x["said"] == best]})
    lex.update(BY_EAR)
    here = pathlib.Path(__file__).parent
    (here / "lexicon.json").write_text(json.dumps(lex, ensure_ascii=False, indent=1))
    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path("results/names.json").write_text(json.dumps({"summary": summary, "trials": rows}, ensure_ascii=False, indent=1))
    return {"lexicon": lex, "summary": summary}


def heard_ok(name: str, heard: str) -> bool:
    """Name counts as heard right if any word run in the transcript sounds right."""
    words = [_norm(w) for w in re.findall(r"[\w\u00C0-\u024F]+", heard)]
    ok = SOUNDS_RIGHT.get(name, [_norm(name)])
    return any("".join(words[i:j]) in ok for i in range(len(words)) for j in range(i + 1, min(i + 4, len(words)) + 1))


def respell(text: str, lexicon: dict | None = None) -> str:
    if lexicon is None:
        p = pathlib.Path(__file__).parent / "lexicon.json"
        lexicon = json.loads(p.read_text()) if p.exists() else {}
    for name, said in lexicon.items():
        text = re.sub(rf"\b{re.escape(name)}\b", said, text)
    return text


if __name__ == "__main__":
    out = learn()
    for s in out["summary"]:
        print(f"{s['name']:<12} raw {s['raw_plain']} (keyterm {s['raw_keyterm']}) -> {s['respelling']} | raw heard {s['heard_raw']} | fixed heard {s['heard_respelled']}")
