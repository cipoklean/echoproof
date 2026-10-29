"""Test cases. `expect` lists what a listener must hear (compared after canon())."""
CASES = [
    # --- Trojan Speech: screen and voice can disagree ---
    {"id": "bidi-account", "cat": "trojan", "text": "Pay to account \u202e9876\u202c now.", "expect": ["6789"],
     "note": "Screen shows 6789; does the voice say 6789?"},
    {"id": "bidi-amount", "cat": "trojan", "text": "Transfer $\u202e002\u202c to the vendor.", "expect": ["200"],
     "note": "Screen shows $200"},
    {"id": "bidi-code", "cat": "trojan", "text": "Your verification code is \u202e4321\u202c.", "expect": ["1234"]},
    {"id": "homoglyph-paypal", "cat": "trojan", "text": "Log in to p\u0430ypal.com.", "expect": ["paypal"]},
    {"id": "homoglyph-bank", "cat": "trojan", "text": "Call your b\u0430nk at the number on your c\u0430rd.", "expect": ["bank", "card"]},
    {"id": "zwsp-number", "cat": "trojan", "text": "Send 1\u200b500 dollars.", "expect": ["1500"]},
    {"id": "fullwidth-pin", "cat": "trojan", "text": "Your PIN is \uff11\uff12\uff13\uff14.", "expect": ["1234"]},
    {"id": "softhyphen-word", "cat": "trojan", "text": "Do n\u00adot transfer the funds.", "expect": ["not"]},
    # --- Money ---
    {"id": "usd-decimal", "cat": "money", "text": "Your balance is $1,500.50, not $15,050.00.", "expect": ["1500", "50", "15050"]},
    {"id": "eur-format", "cat": "money", "text": "The total is \u20ac1.500,00.", "expect": ["1500"]},
    {"id": "negative", "cat": "money", "text": "Refund: -$45.20.", "expect": ["minus", "45"]},
    # --- Medicine ---
    {"id": "dose-decimal", "cat": "medicine", "text": "Take 0.5 mg twice daily. Never take 5 mg.", "expect": ["0.5", "5"]},
    {"id": "dose-ml", "cat": "medicine", "text": "Inject 2.5mL, not 25 mL.", "expect": ["2.5", "25"]},
    # --- Codes ---
    {"id": "leading-zeros", "cat": "codes", "text": "Your code is 007 0090.", "expect": ["0070090"]},
    {"id": "account-10", "cat": "codes", "text": "Account number 0123456789.", "expect": ["0123456789"]},
    # --- Dates ---
    {"id": "date-ambiguous", "cat": "dates", "text": "Your appointment is on 03/04/2026.", "expect": ["2026"],
     "note": "Listen for US (March 4) vs UK (3 April) reading"},
    # --- Names ---
    {"id": "names", "cat": "names", "text": "Siobhan, Aoife, Xochitl and Nguyen joined the call.", "expect": ["siobhan", "aoife", "xochitl", "nguyen"]},
    # --- Other languages ---
    {"id": "de-money", "cat": "money", "lang": "german", "stt": "de", "text": "Der Betrag ist 1.500,50 Euro.", "expect": ["1500"]},
    {"id": "fr-phone", "cat": "codes", "lang": "french", "stt": "fr", "text": "Appelez le 01 42 68 53 00.", "expect": ["0142685300"]},
    {"id": "es-bidi", "cat": "trojan", "lang": "spanish", "stt": "es", "text": "Pague a la cuenta \u202e9876\u202c hoy.", "expect": ["6789"]},
]
