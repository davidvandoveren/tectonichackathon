# Brainstorm – KBC personalization at scale

Status: draft for team discussion. Add your own ideas via PR.

## Framing

The brief asks for a *scalable approach to understanding, supporting and guiding customers*. Every idea below is built from the same four layers; what differs is the "hero" experience we demo.

```
Signals → Understanding (situation / behavior / intent) → Decision (what, when, which channel) → Experience (adapts per customer) 
   ▲                                                                                           │
   └──────────────────── feedback + consent + explainability ◀─────────────────────────────────┘
```

**Design principles:** privacy & consent first · explainable ("why am I seeing this?") · human in control · cheap at 2.3M customers (expensive models only where they add value) · works across app, web, branch, advisor and voice.

## Candidate ideas

### 1. Moments Engine – life-event detection
Detect "moments that matter" (first job, moving, baby, buying a home, retirement, business start, unexpected expense) from transaction patterns, app behavior and product holdings. Trigger the *right* help at the right time (e.g. mortgage simulator, insurance check, savings plan) – or stay silent when nothing is useful.
- Demo: timeline of a synthetic customer; moment detected → tailored journey appears.
- Scale: lightweight scoring on event stream for everyone; LLM only to compose the message.
- Risk: looks like "a recommender" → stress the *moment + silence* logic and explainability.

### 2. Customer Context Graph + Journey Composer (platform vision)
One living "context profile" per customer (situation, goals, preferences, consent), exposed through an API. A composer assembles the next best step from reusable building blocks (cards, forms, simulators, advisor hand-off) across channels.
- Demo: same customer seen in app, web, and advisor screen with consistent context.
- Strong on *fit* (across products/channels/scale) and *technical ability*.

### 3. Generative / server-driven UI – "an app per customer"
App layout, language level, content density and actions are composed per customer (segment of one) from a safe component library and policy guardrails. Example: a student, a pensioner and a SME owner open the same app and get three different home screens.
- Demo: side-by-side personas, live regeneration when context changes.
- Risk: compliance → LLM chooses from approved components only, never free-form numbers.

### 4. Proactive voice companion (ElevenLabs)
A voice-first guide for customers who struggle with apps (older customers, low digital literacy, accessibility). Proactively calls/notifies on relevant moments ("your card expires, want me to order a new one?") and adapts tone, pace and language (NL/FR/EN).
- Demo: short conversation with real voice; handoff to a human advisor.
- High creativity/wow factor; combine with idea 1 for the trigger logic.

### 5. "Financial Twin" – simulate futures before deciding
A personal simulation of the customer's finances; the customer (or advisor) asks "what if I buy a house / go part-time / have a child?" and sees paths with KBC products woven in. The system learns goals and nudges progress.
- Demo: sliders + natural-language what-ifs.
- Risk: regulatory advice boundaries → present as scenarios, not advice.

### 6. Trust layer – consent, control and "why this?"
A cross-cutting differentiator: customers see which signals are used, can switch signals off, and every suggestion carries a plain-language explanation. Turns personalization into a *relationship* rather than surveillance.
- Can be added to any idea above; probably what separates us on creativity + fit.

### 7. Advisor copilot – scale human attention
Instead of only automating towards the customer, prioritise which customers need a human *today* and brief the advisor (context, likely intent, suggested talking points). Scales relationships, not only messages.

## Scale strategy (answers guiding question 5)

- **Tiered intelligence:** rules/light ML for all 2.3M → LLM only for shortlisted moments → human for high-value/sensitive cases.
- **Event-driven:** stream signals (Pub/Sub), precompute profiles, compose on demand, cache aggressively.
- **Cost guardrails:** token budgets, batching, small models for classification, large model for composition.
- **Evaluation at scale:** synthetic personas + simulated customer journeys + guardrail tests; A/B hooks in the design.

## Data (no real customer data!)

Generate a **synthetic population** (e.g. 50–500 personas with transactions, product holdings, app events, life events) with a script in this repo. Keep seeds reproducible so everyone's demo looks the same.

## Possible tech stack (to decide)

- Backend: Python (FastAPI) or TypeScript (Node) – pick what the team knows best
- Frontend: Next.js / React (or plain Vite) for the demo UI
- AI: Gemini on Google Cloud (Vertex AI), ElevenLabs for voice; Cursor for coding
- Data/infra: BigQuery or SQLite/DuckDB for the demo, Cloud Run if we deploy
- Security: run Aikido AI Code Audit early (baseline) and again at the end (10% of score)

## Quick scoring (1–5, discuss & adjust)

| Idea | Creativity | Technical | Fit | Feasible in a day | Notes |
|---|---|---|---|---|---|
| 1 Moments Engine | 3 | 4 | 5 | 5 | Solid core, needs a twist |
| 2 Context graph + composer | 3 | 5 | 5 | 3 | Great platform story, heavy |
| 3 Generative UI | 4 | 4 | 4 | 4 | Very demoable |
| 4 Voice companion | 5 | 3 | 3 | 4 | Wow factor |
| 5 Financial Twin | 4 | 3 | 3 | 3 | Advice-boundary risk |
| 6 Trust layer | 4 | 3 | 4 | 5 | Add-on to any idea |
| 7 Advisor copilot | 3 | 3 | 4 | 4 | Underused angle |

**Suggested starting point (for discussion):** Moments Engine (1) as the intelligence core + Generative UI (3) or Voice (4) as the hero demo + Trust layer (6) as the differentiator. One persona, one moment, end-to-end, then widen.

## Open questions

- Which customer segment / moment do we demo first?
- Do we want a voice demo (ElevenLabs) or visual only?
- Stack and deployment target (local demo vs Cloud Run)?
- Who owns: data generator, decision engine, UI, demo video, security pass?
