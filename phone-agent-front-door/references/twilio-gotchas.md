# Twilio gotchas: the failure catalogue

Four failures cost a working day between them. Each one looks like a different
problem, and each has a check that takes a minute.

---

## 1. The number never rings

**Symptom.** Callers get "the number you have dialled is incorrect" or a fast busy
from their own carrier. The Twilio console shows the number active and the voice
webhook set. The call log has **no inbound record at all**.

**Cause.** The number is provisioned in a region the account does not serve for
inbound, or the DID was never live for PSTN routing. Configuration is irrelevant:
the call never reaches Twilio.

**Check.**

1. Look at the call log. Filter for `direction=inbound`. If there has never been a
   single inbound record, it is not your code.
2. Compare the number's region with the account's region. They must agree.
3. Place a call from Twilio to the number. A call that is accepted and then fails in
   about a second, at zero cost and with no error code, is the same signal.

**Fix.** Move the number to the matching region (or buy one that is already there),
then test again. After the fix the next call appears in the log as `direction=inbound`
within seconds.

**Do not** spend the day rewriting your webhook handler for this. The webhook was
never reached.

---

## 2. The call arrives and the line says goodbye

**Symptom.** An inbound record now exists. The caller hears a single word and a
hangup. Your own tests all pass.

**Cause.** Signature verification is rejecting every genuine request. The usual
reasons, in order of frequency:

**a. The wrong auth token.** One account can hold more than one valid token, and both
authenticate against the REST API while only one signs webhooks. Verifying the token
against the API proves validity and proves nothing about signing.

**b. Blank parameters dropped.** A real inbound POST carries parameters with empty
values (geography fields, forwarded-from, parent call). Twilio signs them as empty
strings. `urllib.parse.parse_qs` drops them by default, so the string you rebuild is
shorter than the one that was signed. Use `keep_blank_values=True`.

**c. The URL rebuilt differently.** Twilio signs the full URL it called, including
the query string. Behind a proxy the origin may see `http` for an `https` call, or a
different `Host`. Test the plausible set of readings.

**d. Too many parameters assumed.** A real call carries far more parameters than a
hand-written test: around two dozen, including a token parameter whose value arrives
double-encoded.

**Check.** Capture one real request in full (method, URL, headers, body) **from
`/voice`**, and log on failure: the supplied signature, the URL candidates tried, and
the parameter *names* with their lengths. Never log the rebuilt payload containing
values, and never capture `/pin` or `/ask` at all: their bodies carry the caller's
digits and words, and a valid signature replays forever.

Then replay the captured `/voice` body with its own signature. If the replay fails,
the token or the URL is wrong. If it succeeds, your live path is rebuilding something
different.

**Treat any captured request as a credential.** Twilio signatures carry no timestamp or
nonce, so a captured body is replayable indefinitely. Keep it mode `0600`, use it
against `/voice` only, and delete it when the test passes.

**Fix.** Prefer the signing token for that account, keep blank values, test candidate
URLs, and pin the replay as a regression test.

---

## 3. The signature covers more of the URL than you think

**Symptom.** The entry point validates fine, then every redirect or follow-up request
fails and the caller hears the fallback message.

**Cause.** The validation code rebuilt `scheme://host/path` and dropped `?query=`.
Twilio signed the whole thing.

**Check.** Log the exact string you build next to the request's real URL. They will
differ by the query string.

**Fix.** Rebuild `path` **and** `query`. The starter script does this in
`candidate_urls()`.

---

## 4. The webhook times out mid-call

**Symptom.** The menu answers, the caller presses 4, and the line goes silent and
then drops.

**Cause.** The handler waited for a model. Providers expect a response in roughly
fifteen seconds; anything slower is treated as failure and the caller hears nothing.

**Fix.** Answer immediately with a holding phrase and a redirect, then return the
real result on the next request. Two requests, one call, no dead air.

---

## Verifying without a phone

You can prove most of the path before dialling:

```bash
python3 scripts/doctor.py     # credentials and one live API call
```

Then replay a captured request:

```bash
curl -s -X POST https://your-host/voice \
  -H "X-Twilio-Signature: <the captured value>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-binary @captured.body
```

Expect the menu. Then change one character in the body and expect a rejection. Both
results together mean the check is real; the first alone means nothing. Delete
`captured.body` afterwards, and never point this at `/pin` or `/ask`.

## A note on what logs should hold

Log the event, the caller number, and the duration. Do not log the transcript, the
question text, or anything the call was about. A phone call is the most private
channel your agent will ever have, and the log outlives the call.
