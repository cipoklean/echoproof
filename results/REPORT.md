# First run (Oct 29, 2026)

TTS-1 voice aai-jane, STT Universal-3.5 Pro (Sync API). STT transcript is evidence, not ground truth.

| Case | Raw heard | Raw | Guarded |
|---|---|---|---|
| bidi-account | Pay to account 9876 now. | FAIL | PASS |
| bidi-amount | Transfer $2 to the vendor. | FAIL | PASS |
| bidi-code | Your verification code is 4321. | FAIL | PASS |
| homoglyph-paypal | Log in to p-hypol.com. | FAIL | PASS |
| homoglyph-bank | Call your bank at the number on your cord. | FAIL | PASS |
| zwsp-number | Send $1,500. | PASS | PASS |
| fullwidth-pin | Your PIN is 1234. | PASS | PASS |
| softhyphen-word | Do not transfer the funds. | PASS | PASS |
| usd-decimal | Your balance is $1,500.50, not $15,050. | PASS | PASS |
| eur-format | The total is €1,500. | PASS | PASS |
| negative | Refund minus $45.20. | PASS | PASS |
| dose-decimal | Take 0.5 milligrams twice daily, never take 5 milligrams. | PASS | PASS |
| dose-ml | Inject 2.5 milliliters, not 25 milliliters. | PASS | PASS |
| leading-zeros | Your code is 0070090. | PASS | PASS |
| account-10 | Account number 0123456789. | PASS | PASS |
| date-ambiguous | Your appointment is on March 4th, 2026. | PASS | PASS |
| names | Siobhan, Aifa, Sochitel, and Nguyen joined the call. | FAIL | FAIL |
| de-money | Der Betrag ist 1.500.500. | FAIL | FAIL |
| fr-phone | Appelez le 01 42 68 53 00. | PASS | PASS |
| es-bidi | PEG a la cuenta: $98.76 hoy. | FAIL | PASS |

Raw failures: 8/20. Guarded failures: 2/20.
