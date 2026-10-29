from echoproof.guard import guard
from echoproof.numbers import canon

def test_bidi_display_and_clean():
    g = guard("Pay to account \u202e9876\u202c now.")
    assert g.displayed == "Pay to account 6789 now."
    assert g.cleaned == "Pay to account 6789 now."
    assert any(f.kind == "bidi_control" for f in g.findings)

def test_homoglyph():
    g = guard("p\u0430ypal.com")
    assert g.cleaned == "paypal.com" and g.findings[0].kind == "homoglyph"

def test_fullwidth_and_zwsp():
    assert guard("\uff11\uff12\uff13\uff14").cleaned == "1234"
    assert guard("1\u200b500").cleaned == "1500"

def test_canon():
    assert "1500" in canon("one thousand five hundred dollars").replace(" ", "")
    assert "9876" in canon("nine eight seven six").replace(" ", "")
    assert "0070090" in canon("zero zero seven zero zero nine zero").replace(" ", "")
    assert "1500" in canon("$1,500.50").replace(" ", "")

def test_superscript_keeps_meaning():
    assert "power of 2" in guard("10\u00b2 units").cleaned

def test_tag_and_foreign_digits():
    assert guard("Pay $50" + "".join(chr(0xE0000+ord(c)) for c in "0") ).cleaned == "Pay $50"
    assert guard("\u0663\u0667").cleaned == "37"

def test_euro_grouping():
    assert "1500.50" in canon("1.500,50 Euro").replace(" ", "")
    from echoproof.run import missing
    assert missing(["1500.50"], "1.500,50 Euro") == []
    assert missing(["1500.50"], "1.500.500") == ["1500.50"]
    assert missing(["1500"], "15000") == ["1500"]

def test_dates_by_locale():
    assert "3 April 2026" in guard("on 03/04/2026", "en-gb").cleaned
    assert "March 4, 2026" in guard("on 03/04/2026", "en-us").cleaned
    assert any(f.kind == "ambiguous_date" for f in guard("03/04/2026", "en-ng").findings)
    assert guard("03/04/2026", "es").cleaned == "03/04/2026"  # TTS-1 reads es/de/fr day-first already
    assert not guard("25/12/2026", "en-gb").findings

def test_names_lexicon():
    from echoproof.names import heard_ok, respell
    assert respell("Aoife and Niamh", {"Aoife": "Eefa", "Niamh": "Neev"}) == "Eefa and Neev"
    assert heard_ok("Saoirse", "Sirsha joined")      # correct sound, phonetic spelling
    assert not heard_ok("Aoife", "Haifa joined")      # wrong sound

def test_locale_numbers():
    assert guard("The price is ₹1,50,000.").cleaned == "The price is 150,000 rupees."
    assert guard("Der Betrag ist 1.500,50 Euro.", "de").cleaned == "Der Betrag ist 1500 Euro und 50 Cent."
    assert guard("Le montant est de 1 500,50 €.", "fr").cleaned == "Le montant est de 1 500,50 €."
    from echoproof.guard import check_voice
    assert check_voice("aai-jane", "german") and not check_voice("aai-jorg", "german")
