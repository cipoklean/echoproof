# EchoProof test matrix

111 runs (57 cases x native voice + aai-jane), TTS-1 -> AssemblyAI Sync STT (Universal-3.5 Pro).
Raw failures were re-transcribed with local Whisper (small); `tts_fault` = both transcribers missed the same value.

**Raw failures: 40/111. Guarded failures: 8/111.**

| Category | Runs | Raw fail | Guarded fail |
|---|---|---|---|
| trojan | 43 | 32 | 0 |
| money | 23 | 3 | 3 |
| medicine | 14 | 1 | 1 |
| codes | 17 | 0 | 0 |
| dates | 10 | 0 | 0 |
| names | 4 | 4 | 4 |

## Every failure

| Case | Voice | Screen shows | Heard (raw) | Verdict | Guarded |
|---|---|---|---|---|---|
| en-rlo-account | aai-audrey | Pay to account 6789 now. | Pay to account 9876 now. | tts_fault | PASS |
| en-rlo-account | aai-jane | Pay to account 6789 now. | Pay to account 9876 now. | tts_fault | PASS |
| en-rlo-amount | aai-audrey | Transfer $200 to the vendor. | Transfer $2 to the vendor. | tts_fault | PASS |
| en-rlo-amount | aai-jane | Transfer $200 to the vendor. | Transfer $2 to the vendor. | tts_fault | PASS |
| en-rlo-amount-big | aai-audrey | Approve the payment of $10000. | Approved the payment of $1. | tts_fault | PASS |
| en-rlo-amount-big | aai-jane | Approve the payment of $10000. | Approve the payment of $1. | tts_fault | PASS |
| en-rli-code | aai-audrey | Your verification code is 1234. | Your verification code is 4321. | tts_fault | PASS |
| en-rli-code | aai-jane | Your verification code is 1234. | Your verification code is 4321. | tts_fault | PASS |
| en-rlo-iban | aai-audrey | Send to IBAN GB29 5678 1234 0001. | Send to IBAN GB29432187650001. | tts_fault | PASS |
| en-rlo-iban | aai-jane | Send to IBAN GB29 5678 1234 0001. | Send to IBAN: GB29432187650001. | tts_fault | PASS |
| en-rlo-date | aai-audrey | Your deadline is May 10, 2025. | Your deadline is 5/20/201, yam. | tts_fault | PASS |
| en-rlo-date | aai-jane | Your deadline is May 10, 2025. | Your deadline is 5/202/01, Yam. | tts_fault | PASS |
| en-homoglyph-paypal | aai-audrey | Log in to pаypal.com to confirm. | Log in to phppl.com to confirm. | tts_fault | PASS |
| en-homoglyph-paypal | aai-jane | Log in to pаypal.com to confirm. | Log in to phipal.com to confirm. | tts_fault | PASS |
| en-homoglyph-bank | aai-audrey | Call your bаnk at the number on your cаrd. | Call your Bink at the number on your cord. | tts_fault | PASS |
| en-homoglyph-bank | aai-jane | Call your bаnk at the number on your cаrd. | Call your bank at the number on your cord. | tts_fault | PASS |
| en-greek-amazon | aai-jane | Your Αmazon order has shipped. | Your Nimazon order has shipped. | tts_fault | PASS |
| en-arabic-digits | aai-audrey | Your code is ٣٧٢٩. | Your code is BABBW. | tts_fault | PASS |
| en-arabic-digits | aai-jane | Your code is ٣٧٢٩. | Your code is ba ba ba. | tts_fault | PASS |
| en-superscript | aai-audrey | Dose: 10² units. | Dose: 10 W units. | tts_fault | PASS |
| en-superscript | aai-jane | Dose: 10² units. | Dose: 10 units. | tts_fault | PASS |
| en-fraction | aai-audrey | Take ½ tablet. | Take Mark tablet. | tts_fault | PASS |
| en-fraction | aai-jane | Take ½ tablet. | Take mole tablet. | tts_fault | PASS |
| es-rlo-account | aai-constanza | Pague a la cuenta 6789 hoy. | Pague a la cuenta 9876 hoy. | tts_fault | PASS |
| es-rlo-account | aai-jane | Pague a la cuenta 6789 hoy. | PEG a la cuenta: $98.76 hoy. | tts_fault | PASS |
| de-rlo-amount | aai-jorg | Überweisen Sie 500 Euro. | Überweisen Sie 005 Euro. | tts_fault | PASS |
| de-rlo-amount | aai-jane | Überweisen Sie 500 Euro. | Überweisen Sie 005 Euro. | tts_fault | PASS |
| fr-rlo-code | aai-donatien | Votre code est 1234. | Votre code est 4321. | tts_fault | PASS |
| fr-rlo-code | aai-jane | Votre code est 1234. | Votre code est 4321. | tts_fault | PASS |
| pt-rlo-account | aai-benicio | Pague na conta 6789 hoje. | Pague na conta 9876 hoje. | tts_fault | PASS |
| pt-rlo-account | aai-jane | Pague na conta 6789 hoje. | Pegna Conta 9876 OG. | tts_fault | PASS |
| it-rlo-amount | aai-jane | Paga 200 euro adesso. | Paga €002 adesso. | tts_fault | PASS |
| en-inr-lakh | aai-audrey | The price is ₹1,50,000. | The price is $105,000. | tts_fault | FAIL: The price is $105,000. |
| de-money | aai-jane | Der Betrag ist 1.500,50 Euro. | Der Betrag ist 1.500.500. | tts_fault | FAIL: Der Betrag ist 1.500.500. |
| it-money | aai-jane | Il totale è 1.500,50 euro. | Il totale è 1.50050 euro. | tts_fault | FAIL: Il totale è 1.50050 euro. |
| de-dose | aai-jane | Nehmen Sie 2,5 mg täglich. | Name and C 25 mg täglich. | tts_fault | FAIL: Name and C 25 mg täglich. |
| en-names-irish | aai-audrey | Siobhan, Aoife and Niamh joined the call. | Siobhan, Oifa, and Niamh join the call. | tts_fault | FAIL: Siobhan, Oifa, and Niamh join the call. |
| en-names-irish | aai-jane | Siobhan, Aoife and Niamh joined the call. | Siobhan, Aifa, and Niamh joined the call. | tts_fault | FAIL: Siobhan, Aifa, and Niamh joined the call. |
| en-names-global | aai-audrey | Xochitl, Nguyen, Chukwuemeka and Saoirse are here. | So Chitul, Nwen, Chukwuemeka, and Sirsha are here. | tts_fault | FAIL: So Chitul, Nwen, Chukwuemeka, and Sirsha are here. |
| en-names-global | aai-jane | Xochitl, Nguyen, Chukwuemeka and Saoirse are here. | Zochitl, Nwin, Chukwumeka, and Sirsha are here. | tts_fault | FAIL: Zochitl, Nwin, Chukwumeka, and Sirsha are here. |
