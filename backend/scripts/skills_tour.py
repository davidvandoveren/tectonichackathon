"""A guided tour of Kate Skills, end to end, in one command. No server, keys or password needed.

    cd backend && python scripts/skills_tour.py            # everything, as Emma
    python scripts/skills_tour.py --persona jan            # another customer

It drives the real API in-process (same code as production) and prints what a customer would see:
the catalogue, the consent ladder, feed cards with a confirm button, a mandate that lets Kate act on
her own, the guardrails that stop her, and the activity log.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DEMO_PASSWORD", "skills-tour")

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

WHY = "Rondleiding Kate Skills"


def title(text: str) -> None:
    print(f"\n=== {text} " + "=" * max(0, 70 - len(text)))


def show(label: str, response: Any) -> Any:
    body = response.json() if response.content else None
    print(f"  {label}: HTTP {response.status_code}")
    return body


def tour(client: TestClient) -> None:
    title("1. Wat kan Kate? (GET /skills)")
    for skill in client.get("/api/v1/skills").json():
        print(f"  {skill['title']}")
        for a in skill["actions"]:
            print(
                f"    - {a['id']:<28} {a['risk']:<15} staat op {a['level']:<8} max {a['max_level']}"
            )

    title("2. Kate-feed met Bevestig-knoppen (GET /kate/feed + /skills/feed-actions)")
    feed = client.get("/api/v1/kate/feed").json()
    actions = {a["moment"]: a for a in client.get("/api/v1/skills/feed-actions").json()}
    for item in feed["items"]:
        action = actions.get(item["id"])
        button = (
            f"[Bevestig: {action['summary']}]"
            if action and action["can_confirm"]
            else "(geen knop)"
        )
        print(f"  • {item['title']}  (urgentie {item['urgency']}, kanaal {item['channel']})")
        print(f"    {button}")
    for silence in feed["silenced"]:
        print(f"  ∅ bewust stil over {silence['moment']}: {silence['reason']}")

    if actions:
        moment = next(iter(actions))
        title(f"3. Klant tikt op Bevestig bij '{moment}'")
        proposal = show(
            "POST /proposals/from-moment",
            client.post("/api/v1/proposals/from-moment", json={"moment": moment}),
        )
        print(f"    voorstel: {proposal['summary']} (status {proposal['status']})")
        print(f"    waarom:   {proposal['reason'][:110]}…")
        done = show(
            "POST /proposals/{id}/approve",
            client.post(f"/api/v1/proposals/{proposal['id']}/approve", json={}),
        )
        print(f"    resultaat ({done['outcome']['kind']}): {done['outcome']['message']}")

    title("4. Mandaat: Kate mag zelf tot € 50 per keer, € 100 per maand opzij zetten")
    show(
        "PUT /skills/consent/savings.move_to_savings",
        client.put(
            "/api/v1/skills/consent/savings.move_to_savings",
            json={
                "level": "auto",
                "mandate": {"max_per_execution": "50.00", "max_per_month": "100.00"},
            },
        ),
    )
    for amount in ("40.00", "40.00", "40.00"):
        p = client.post(
            "/api/v1/proposals",
            json={
                "action": "savings.move_to_savings",
                "params": {"amount": amount},
                "source": "moment",
                "reason": WHY,
            },
        ).json()
        note = (
            "Kate deed het zelf"
            if p["status"] == "executed"
            else "boven het mandaat → vraagt eerst"
        )
        print(f"    € {amount}: {p['status']:<9} ({note})")

    title("5. Grenzen die Kate nooit overschrijdt")
    checks = [
        (
            "iemand anders betalen automatisch zetten",
            client.put("/api/v1/skills/consent/payments.transfer", json={"level": "auto"}),
        ),
        (
            "mandaat boven het plafond (€ 900)",
            client.put(
                "/api/v1/skills/consent/savings.move_to_savings",
                json={
                    "level": "auto",
                    "mandate": {"max_per_execution": "900.00", "max_per_month": "900.00"},
                },
            ),
        ),
        (
            "moment verzinnen dat niet in je feed staat",
            client.post("/api/v1/proposals/from-moment", json={"moment": "idle_savings_fake"}),
        ),
    ]
    for label, response in checks:
        print(f"    {label}: HTTP {response.status_code} - {response.json().get('detail', '')}")
    transfer = client.post(
        "/api/v1/proposals",
        json={
            "action": "payments.transfer",
            "params": {"to_name": "Lucas", "amount": "25.00", "description": "Pizza"},
            "source": "chat",
            "reason": "Je vroeg om Lucas 25 euro te sturen.",
        },
    ).json()
    done = client.post(f"/api/v1/proposals/{transfer['id']}/approve", json={}).json()
    outcome = done["outcome"]
    print(f"    overschrijving naar Lucas: {outcome['kind']} → {outcome['navigate_to']}")
    loan = client.post(
        "/api/v1/proposals",
        json={
            "action": "loans.explore",
            "params": {"purpose": "home", "amount": "250000.00"},
            "source": "chat",
            "reason": "Je vroeg naar een woonkrediet.",
        },
    ).json()
    done = client.post(f"/api/v1/proposals/{loan['id']}/approve", json={}).json()
    print(f"    woonkrediet: {done['outcome']['kind']} → {done['outcome']['handoff_summary']}")

    title("6. Uitzetten: Kate mag geen kaartpakketten meer voorstellen")
    client.put("/api/v1/skills/consent/cards.add_package", json={"level": "off"})
    refused = client.post(
        "/api/v1/proposals",
        json={
            "action": "cards.add_package",
            "params": {"package": "reis"},
            "source": "chat",
            "reason": WHY,
        },
    )
    print(f"    voorstel Reispakket: HTTP {refused.status_code} - {refused.json()['detail']}")

    title("7. Wat heeft Kate voor mij gedaan? (GET /activity)")
    for entry in client.get("/api/v1/activity").json()[:12]:
        print(f"    {entry['event']:<16} {entry['summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--persona", default="emma", help="any demo persona, e.g. sofie or bram")
    args = parser.parse_args()
    # Windows consoles default to cp1252; the tour prints € and arrows.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    settings = Settings(
        app_env="test",
        demo_password=os.environ["DEMO_PASSWORD"],  # type: ignore[arg-type]
        cookie_secure=False,
    )
    with TestClient(create_app(settings)) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": args.persona, "password": os.environ["DEMO_PASSWORD"]},
        )
        if login.status_code != 200:
            names = [u["username"] for u in client.get("/api/v1/auth/demo-users").json()]
            sys.exit(f"Onbekende persona '{args.persona}'. Kies uit: {', '.join(names)}")
        print(f"Ingelogd als {args.persona}")
        tour(client)


if __name__ == "__main__":
    main()
