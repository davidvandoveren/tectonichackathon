# Builderbase submission – Kate 2.0

Draft project description for the Builderbase form. Owner: Alexandre (#42). Numbers marked
**(PR #n)** come from work that is still in review: re-check them once it is on `main`, and delete
anything that did not make it before submitting. The final submission cannot be changed.

---

## Title

**Kate 2.0 – situations that are composed, not written**

## One-liner (≤ 200 characters)

Kate 2.0 builds each customer's moments from reusable signals, then decides what is worth
saying, when, through which channel – and when to deliberately say nothing.

## Short description

KBC's Kate already reaches out proactively, in more than 140 hand-written situations. You cannot
hand-write a segment of one for 2.3 million customers. Kate 2.0 is the brain behind the next
Kate: a catalogue of cheap, explainable **signals** (a salary that is late, a deposit-sized
payment, a savings habit done by hand) combines into **moments** that nobody pre-programmed, each
with a confidence score. An **arbitration** layer then decides what is worth saying, when, and
through which channel: a feed card, a push, an SMS or a call. It also decides when to say
nothing, and explains why.

Everything the customer sees says *"Waarom zie ik dit?"* in their own numbers. Customers switch
data domains off (consent is applied *before* any signal is computed) and set per action how far
Kate may go: suggest, prepare, or act within a mandate they set. Money to someone else, credit,
investing and insurance advice are never automatic. They go to the normal confirmation screen or
to a human advisor. The proactive brain is deterministic Python with no model and no network
call, so it is cheap at scale and cannot fail live. The conversational side (chat and voice,
Gemini and ElevenLabs) only runs when a customer talks to Kate.

## The problem we picked

The brief asks for personalization that works *for millions at the same time* (guiding
question 5). Hand-authored situations scale linearly with people writing them; customers' lives
do not. And the more situations a bank can recognise, the bigger the new risk: spam. A bank that
notices everything and says everything is worse than one that notices nothing.

## What we built (working proof of concept)

- **A simulated KBC Mobile app** (React, mobile/desktop toggle). You can log in as synthetic
  customers, see accounts and transactions, and make server-validated transfers.
- **The Moments Engine** (Kate's brain). It works in four layers: signals → moments → arbitration
  → composition. Urgency bands never overlap, so a risk always outranks an offer. There is at most
  one interruption per week, a 30-day cooldown on "niet meer tonen", and a *save-money asymmetry*:
  an offer that costs money is held back while the customer's buffer is thin, but an offer that
  saves money never is.
- **Deliberate silence as a first-class output.** Every item Kate withholds comes with a reason
  code (`low_confidence`, `cashflow_first`, `dismissed`).
- **Time machine** (admin only): skip a week ahead. The salary does not arrive, and Kate moves
  from the feed to a push, an SMS and a call.
- **Kate chat ("Just say it") and voice.** For example, "Stuur Lucas 25 euro voor de pizza" gives
  a pre-filled transfer that the customer confirms. There is an **inheritance guidance mode** with
  no marketing, a step plan and a hand-off summary for an advisor. Kate has two voices; the
  default follows the customer record, and the customer can always switch.
- **Kate Skills.** Every KBC function (payments, savings, cards, Kate Deals, insurance, loans,
  investing, advisor) plugs in once and is usable from every channel. There is a consent ladder
  per action (`off` / `suggest` / `prepare` / `auto`) with mandates and hard ceilings, plus an
  activity log: "Wat heeft Kate voor mij gedaan?"
- **Subscription manager ("Gebruik je dit nog?").** Subscriptions are detected automatically,
  including duplicates, price increases and trials that converted. The bank never guesses usage;
  the customer answers. Sensitive subscriptions are counted, never shown.
- **Jury dashboard (PR #30).** The real engine runs over **10,000 synthetic customers**:
  54.7 % got something, 10.5 % were interrupted, and **45.3 % deliberately got nothing**. The
  engine takes p50 0.73 ms per customer, which is about 28 CPU-minutes for all 2.3 M KBC
  customers, with no LLM.
- **Personas that each tell one story.** Emma (first salary), Jan (moving house), Marie (retired,
  idle savings), Sofie (manual savings habit, loyal fuel station, unused Luxepakket), Lucas
  (financially tight: warned before the rent, offers held back) and Els (inheritance: Kate stays
  quiet commercially and guides instead).

## Why it fits KBC

- **It builds on Kate instead of replacing her.** The 140 situations stay; new ones are composed
  from signals.
- **It uses KBC's real catalogue.** It suggests the real card packages (Shopping / Reis / Luxe)
  and Kate Deals, and it also suggests *dropping* a package nobody uses. A bank that costs itself
  money is the strongest trust signal we could think of.
- **A human stays in the loop.** Kate proposes and the customer confirms. Regulated topics go to
  an advisor with full context, so the customer never has to repeat their story.

## Scale and cost

The engine is a pure function of one customer's own data and today's date. The same call serves
one customer in a request or millions in a batch job. Signals are computed for everyone at near
zero cost; the LLM is only called when a customer talks to Kate. See the jury dashboard for the
measured numbers (PR #30).

## Security (Aikido)

- **Owner-scoped by construction.** Every data query takes the logged-in user's id, so another
  customer's data is unreachable. Such a request returns `404`, never `403`, so the attacker
  learns nothing. Admin endpoints return `404` to customers.
- **Sessions.** Server-side sessions sit in an `HttpOnly; Secure; SameSite=Strict` `__Host-`
  cookie. Passwords are hashed with scrypt, logins are rate limited, and there is a CSRF guard,
  a strict CSP and security headers.
- **Server-side validation of every transfer.** IBAN mod-97, amount limits and balance checks all
  run on the server. Kate never pays a third party herself.
- **LLM hardening.** Transaction texts go to the model as data, never as instructions, and this is
  tested against prompt injection. Kate only sees the customer's own data, without IBANs. Sensitive
  spending (health, religion, politics, trade union) is never labelled, used for offers or shown.
- **CI and dependencies.** CI runs ruff, mypy (strict), pytest, ESLint, tsc, vitest, pip-audit,
  npm audit and a Docker build. Dependabot is on, and secrets live only in env or Secret Manager.
- **Aikido screenshots, before and after:** *(to add: baseline and final scan)*.

## Honest limitations

- **Data.** All data is synthetic and in memory, and it resets on restart. The next step is a real
  store behind the same owner-scoped interface.
- **Population.** The 10,000-customer population uses an illustrative mix of archetypes, not
  KBC's real distribution.
- **Chat and voice.** Without API keys, chat and voice fall back to a demo mode (canned answers,
  browser speech).
- **Rules.** Moment recipes are weighted rules, not trained models. That is deliberate:
  explainable, cheap and testable. The confidence scores are where learning would plug in.

## Links

- Repository: https://github.com/davidvandoveren/tectonichackathon
- Live demo: *(Cloud Run URL)*
- Demo video: *(link)*
- Design: `docs/design/moments-engine.md`, `docs/design/kate-skills.md`
