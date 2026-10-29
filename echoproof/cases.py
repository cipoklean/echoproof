"""Test matrix. `expect`: values a listener must hear (compared after canon()).

Each case names the language; run.py speaks it with the language's native catalog
voice and with the built-in default voice (aai-jane).
"""
RLO, PDF, RLI, PDI, LRO = "\u202e", "\u202c", "\u2067", "\u2069", "\u202d"
ZW = "\u200b"
def tag(s): return "".join(chr(0xE0000 + ord(c)) for c in s)

LANGS = {  # language -> (TTS language, STT code, native voice)
    "en": ("english", "en", "aai-audrey"),
    "es": ("spanish", "es", "aai-constanza"),
    "de": ("german", "de", "aai-jorg"),
    "fr": ("french", "fr", "aai-donatien"),
    "pt": ("portuguese", "pt", "aai-benicio"),
    "it": ("italian", "it", "aai-jane"),  # no Italian catalog voice in the docs' starter list
}

C = []
def add(id, lang, cat, text, expect, note="", locale=None):
    C.append({"id": id, "lang": lang, "cat": cat, "text": text, "expect": expect, "note": note,
              "locale": locale or {"en": "en-us"}.get(lang, lang)})

# ---------- Trojan Speech (display != speech) ----------
add("en-rlo-account", "en", "trojan", f"Pay to account {RLO}9876{PDF} now.", ["6789"])
add("en-rlo-amount", "en", "trojan", f"Transfer ${RLO}002{PDF} to the vendor.", ["200"])
add("en-rlo-amount-big", "en", "trojan", f"Approve the payment of ${RLO}00001{PDF}.", ["10000"])
add("en-rli-code", "en", "trojan", f"Your verification code is {RLI}4321{PDI}.", ["1234"])
add("en-rlo-iban", "en", "trojan", f"Send to IBAN GB29 {RLO}4321 8765{PDF} 0001.", ["GB29567812340001"])
add("en-rlo-date", "en", "trojan", f"Your deadline is {RLO}5202 ,01 yaM{PDF}.", ["may", "10", "2025"], "screen: May 10, 2025")
add("en-homoglyph-paypal", "en", "trojan", "Log in to p\u0430ypal.com to confirm.", ["paypal"])
add("en-homoglyph-bank", "en", "trojan", "Call your b\u0430nk at the number on your c\u0430rd.", ["bank", "card"])
add("en-greek-amazon", "en", "trojan", "Your \u0391mazon order has shipped.", ["amazon"])
add("en-tag-smuggle", "en", "trojan", f"Pay $50{tag('0 extra')} today.", ["50"], "tag chars invisible on screen")
add("en-zwsp-number", "en", "trojan", f"Send 1{ZW}500 dollars.", ["1500"])
add("en-softhyphen-not", "en", "trojan", "Do n\u00adot transfer the funds.", ["not"])
add("en-fullwidth-pin", "en", "trojan", "Your PIN is \uff11\uff12\uff13\uff14.", ["1234"])
add("en-mathbold-pin", "en", "trojan", "Your PIN is \U0001D7CF\U0001D7D0\U0001D7D1\U0001D7D2.", ["1234"])
add("en-arabic-digits", "en", "trojan", "Your code is \u0663\u0667\u0662\u0669.", ["3729"])
add("en-superscript", "en", "trojan", "Dose: 10\u00b2 units.", ["100|10 to the power of 2|10^2|10 squared"], "screen 10\u00b2 = 100")
add("en-fraction", "en", "trojan", "Take \u00bd tablet.", ["half|1/2"])
add("es-rlo-account", "es", "trojan", f"Pague a la cuenta {RLO}9876{PDF} hoy.", ["6789"])
add("de-rlo-amount", "de", "trojan", f"Überweisen Sie {RLO}005{PDF} Euro.", ["500"])
add("fr-rlo-code", "fr", "trojan", f"Votre code est {RLO}4321{PDF}.", ["1234"])
add("pt-rlo-account", "pt", "trojan", f"Pague na conta {RLO}9876{PDF} hoje.", ["6789"])
add("it-rlo-amount", "it", "trojan", f"Paga {RLO}002{PDF} euro adesso.", ["200"])

# ---------- Money ----------
add("en-usd", "en", "money", "Your balance is $1,500.50, not $15,050.00.", ["1500", "15050"])
add("en-gbp", "en", "money", "The fee is £2,349.99.", ["2349", "99"])
add("en-jpy", "en", "money", "The total is ¥120,000.", ["120000"])
add("en-inr-lakh", "en", "money", "The price is ₹1,50,000.", ["150000"], "Indian grouping")
add("en-negative", "en", "money", "Refund: -$45.20.", ["45"])
add("en-k-suffix", "en", "money", "Your limit is $2.5k per day.", ["2500"])
add("es-money", "es", "money", "El total es 1.500,50 €.", ["1500.50|1500 euros con 50"])
add("de-money", "de", "money", "Der Betrag ist 1.500,50 Euro.", ["1500.50|1500 euro 50"])
add("de-money-small", "de", "money", "Sie zahlen 12,99 Euro.", ["12.99|12 euro 99"])
add("fr-money", "fr", "money", "Le montant est de 1 500,50 €.", ["1500.50|1500 euros 50|1500 euros et 50"])
add("pt-money", "pt", "money", "O valor é R$ 1.500,50.", ["1500.50|mil e quinhentos reais e cinquenta"])
add("it-money", "it", "money", "Il totale è 1.500,50 euro.", ["1500.50|1500 euro e 50"])

# ---------- Medicine ----------
add("en-dose-decimal", "en", "medicine", "Take 0.5 mg twice daily. Never take 5 mg.", ["0.5", "5"])
add("en-dose-ml", "en", "medicine", "Inject 2.5mL, not 25 mL.", ["2.5", "25"])
add("en-dose-mcg", "en", "medicine", "Give 50 mcg of fentanyl.", ["50", "micrograms"])
add("en-dose-trailing-zero", "en", "medicine", "Take 1.0 mg.", ["1"])
add("es-dose", "es", "medicine", "Tome 0,5 mg dos veces al día.", ["0.5|0 coma 5"])
add("de-dose", "de", "medicine", "Nehmen Sie 2,5 mg täglich.", ["2.5|2 komma 5"])
add("fr-dose", "fr", "medicine", "Prenez 0,25 mg le soir.", ["0.25|0 virgule 25"])

# ---------- Codes / phones ----------
add("en-leading-zeros", "en", "codes", "Your code is 007 0090.", ["0070090"])
add("en-account-10", "en", "codes", "Account number 0123456789.", ["0123456789"])
add("en-alnum-code", "en", "codes", "Booking reference: QX7B9Z.", ["qx7b9z"])
add("en-phone-intl", "en", "codes", "Call +44 20 7946 0958.", ["442079460958"])
add("es-phone", "es", "codes", "Llame al +34 912 345 678.", ["34912345678"])
add("de-phone", "de", "codes", "Rufen Sie 030 1234567 an.", ["0301234567"])
add("fr-phone", "fr", "codes", "Appelez le 01 42 68 53 00.", ["0142685300"])
add("pt-phone", "pt", "codes", "Ligue para +351 912 345 678.", ["351912345678"])
add("it-phone", "it", "codes", "Chiami il 06 1234 5678.", ["0612345678"])

# ---------- Dates ----------
add("en-us-date-slash", "en", "dates", "Your appointment is on 03/04/2026.", ["march", "4", "2026"], "US caller", "en-us")
add("en-gb-date-slash", "en", "dates", "Your appointment is on 03/04/2026.", ["april", "3", "2026"], "UK caller", "en-gb")
add("en-ng-date-slash", "en", "dates", "Your clinic visit is on 05/06/2026.", ["june", "5", "2026"], "Nigerian caller", "en-ng")
add("en-in-date-dot", "en", "dates", "Your EMI is due on 11.12.2026.", ["december", "11", "2026"], "Indian caller", "en-in")
add("en-date-iso", "en", "dates", "Your appointment is on 2026-04-03.", ["april", "2026"])
add("es-date-slash", "es", "dates", "Su cita es el 03/04/2026.", ["abril", "2026"])
add("de-date", "de", "dates", "Ihr Termin ist am 03.04.2026.", ["april", "2026"])
add("pt-date-slash", "pt", "dates", "Sua consulta é em 03/04/2026.", ["abril", "2026"])
add("it-date-slash", "it", "dates", "Il suo appuntamento è il 03/04/2026.", ["aprile", "2026"])
add("fr-date-slash", "fr", "dates", "Votre rendez-vous est le 03/04/2026.", ["avril", "2026"])

# ---------- Names ----------
for i, (txt, ns) in enumerate([
    ("Siobhan, Aoife and Niamh joined the call.", ["Siobhan", "Aoife", "Niamh"]),
    ("Xochitl, Chukwuemeka and Saoirse are here.", ["Xochitl", "Chukwuemeka", "Saoirse"]),
    ("Oluwaseun and Siân have confirmed.", ["Oluwaseun", "Siân"]),
]):
    add(f"en-names-{i+1}", "en", "names", txt, ns)
    C[-1]["names"] = ns

CASES = C
