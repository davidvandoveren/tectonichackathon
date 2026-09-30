# Security policy

This is a hackathon prototype (Tectonic Hackathon, KBC case) that runs on **synthetic data only**.
It is not a KBC product and holds no real customer data. We still take reports seriously.

## Reporting a vulnerability

Please report privately via **[GitHub Security Advisories](https://github.com/davidvandoveren/tectonichackathon/security/advisories/new)**.
Do not open a public issue with details. The same contact is published at
`/.well-known/security.txt` on the running app (RFC 9116).

Include what you found, how to reproduce it, and the impact you expect. We aim to acknowledge
within 2 working days (best effort after the hackathon).

## Scope

In scope: the code in this repository and the demo deployment built from it.

Please do **not**:
- run denial-of-service or load tests, or automated scanners at high rates against the demo;
- use social engineering or attack third-party services (Google Gemini, ElevenLabs, GitHub);
- enter real personal data, account numbers or passwords.

Good-faith research within these rules is welcome; we will not pursue it.

## What we already do

See [docs/security-and-compliance.md](docs/security-and-compliance.md) for the controls, the
tests that prove them, and the known limitations of the prototype.
