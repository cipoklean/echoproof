# Live results (2026-10-30 00:26 UTC)

16 sentences x 3 runs = 48 real round trips through https://echoproof-sigma.vercel.app (AssemblyAI TTS-1, then Sync STT). 0 errored.

- As written: **48 of 48** runs said a value wrong.
- With SayGuard: **2 of 48**.

| Sentence | As written: wrong | With SayGuard: wrong | What the caller heard as written (first run) |
|---|---|---|---|
| A hidden right-to-left mark: the screen shows $10000, the characters run 0,0,0,0,1 | 3/3 | 0/3 | Approve the payment of $1. |
| Account number reversed by a hidden mark | 3/3 | 0/3 | Pay to account 9876 now. |
| Part of an IBAN flipped inside a hidden mark | 3/3 | 0/3 | Send to IBAN: GB29432187650001. |
| A whole date written backwards, displayed forwards | 3/3 | 0/3 | Your deadline is 5/20/201, YAM. |
| The 'a' in paypal is Cyrillic | 3/3 | 0/3 | Log in to passy-pull.com to confirm. |
| A code typed with Arabic-Indic digits | 3/3 | 0/3 | Your code is BABBAB. |
| A half written as one character | 3/3 | 0/3 | Take war tablet. |
| A superscript power in a dose | 3/3 | 0/3 | Dose: $10 units. |
| Indian lakh grouping: 1,50,000 is 150,000 | 3/3 | 0/3 | The price is $1,050,000. |
| European decimal comma in an amount | 3/3 | 1/3 | Il totale è $1.500,50. |
| Day-first date for a UK caller | 3/3 | 0/3 | Your appointment is on March 4th, 2026. |
| Day-first date for a Nigerian caller | 3/3 | 0/3 | Your clinic visit is on May 6th, 2026. |
| Yoruba name TTS-1 clips to 'Oluwasun' | 3/3 | 1/3 | Oluwasun and Seyi have confirmed. |
| TTS-1 turns 'eze' into 'easy' | 3/3 | 0/3 | Send the receipt to k.nwosu-easy@un.edu.ng today. |
| German amount reversed by a hidden mark | 3/3 | 0/3 | Überweisen Sie 005 Euro. |
| Spanish account number reversed | 3/3 | 0/3 | Pague a la cuenta 9876 hoy. |

Every transcript is in `results/live.json`.
