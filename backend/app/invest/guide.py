"""The rules behind "Beleggen met Kate": health check, profile, direction and the mix check.

Kate explains and points a healthy direction; the customer chooses. Concretely:
- The **buffer** (3 months of the customer's own expenses, at least € 2.000) is never invested.
- The **profile** follows from horizon and how the customer says they would react to a drop, with
  caps for short horizons. It sets a broad shares/bonds split, not a product.
- The **mix check** marks what fits and warns about what does not. A mismatch is allowed, but only
  after an explicit "ik begrijp het risico". Complex (leveraged) products are refused to customers
  who say they have no investing knowledge (the appropriateness test a bank must do).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_UP, Decimal
from typing import Literal

from app.domain.models import Account, AccountType, Category, Transaction
from app.invest.catalog import BY_ID, Etf

BUFFER_MONTHS = 3
MIN_BUFFER = Decimal("2000")
MIN_INVESTABLE = Decimal("500")
LOOKBACK_DAYS = 90

Goal = Literal["grow", "pension", "purchase", "income"]
Horizon = Literal["lt3", "3to5", "5to10", "gt10"]
Knowledge = Literal["none", "basic", "experienced"]
Reaction = Literal["sell_all", "worried", "wait", "buy_more"]
ProfileName = Literal["defensive", "neutral", "dynamic"]
HealthStatus = Literal["ready", "caution", "build_buffer"]


def eur(amount: Decimal, decimals: int = 2) -> str:
    """Belgian notation for text Kate says: € 9.600 or € 500,00."""
    text = f"{amount:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
    return f"€ {text}"


# --- 1. health check ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Health:
    status: HealthStatus
    savings: Decimal
    monthly_expenses: Decimal
    monthly_income: Decimal
    buffer: Decimal
    investable: Decimal
    savings_account_id: str | None
    notes: tuple[str, ...]


def health_check(
    accounts: Sequence[Account], transactions: Sequence[Transaction], today: date
) -> Health:
    """Only the customer's own accounts and transactions; nothing else is needed."""
    since = today - timedelta(days=LOOKBACK_DAYS)
    recent = [t for t in transactions if since < t.booked_at <= today]
    # Own money moving between own accounts is neither income nor spending.
    outflow = -sum(
        (t.amount for t in recent if t.amount < 0 and t.category not in _INTERNAL), Decimal(0)
    )
    inflow = sum(
        (t.amount for t in recent if t.amount > 0 and t.category == Category.INCOME), Decimal(0)
    )
    months = Decimal(LOOKBACK_DAYS) / Decimal(30)
    expenses = (outflow / months).quantize(Decimal("1"), ROUND_UP)
    income = (inflow / months).quantize(Decimal("1"), ROUND_UP)
    buffer = max(MIN_BUFFER, _round_up_100(expenses * BUFFER_MONTHS))

    savings_accounts = sorted(
        (a for a in accounts if a.type == AccountType.SAVINGS),
        key=lambda a: a.balance,
        reverse=True,
    )
    savings = sum((a.balance for a in savings_accounts), Decimal(0))
    main_savings = savings_accounts[0] if savings_accounts else None
    # A plan draws from one savings account, so only that account's surplus counts.
    investable = max(Decimal(0), (main_savings.balance if main_savings else Decimal(0)) - buffer)

    notes: list[str] = []
    status: HealthStatus = "ready"
    if investable < MIN_INVESTABLE:
        status = "build_buffer"
        notes.append(
            f"Eerst een buffer: hou minstens {BUFFER_MONTHS} maanden vaste kosten "
            f"(± {eur(buffer, 0)}) op je spaarrekening voor onverwachte uitgaven. Beleggen doe je "
            "met geld dat je jaren kan missen."
        )
    if income and expenses > income:
        status = "caution" if status == "ready" else status
        notes.append(
            "Je gaf de voorbije maanden meer uit dan er binnenkwam. Kijk eerst of dat tijdelijk is "
            "voor je begint te beleggen."
        )
    credit = sum((a.balance for a in accounts if a.type == AccountType.CREDIT_CARD), Decimal(0))
    if credit < Decimal("-1000"):
        status = "caution" if status == "ready" else status
        notes.append(
            "Er staat een groot bedrag open op je kredietkaart. Schulden aflossen levert vaak meer "
            "op dan beleggen."
        )
    if status == "ready":
        notes.append(
            f"Je buffer van {eur(buffer, 0)} blijft altijd op je spaarrekening. Wat erboven staat "
            f"({eur(investable, 0)}) kan je, als je dat wil, stap voor stap beleggen."
        )
    return Health(
        status=status,
        savings=savings,
        monthly_expenses=expenses,
        monthly_income=income,
        buffer=buffer,
        investable=investable,
        savings_account_id=main_savings.id if main_savings else None,
        notes=tuple(notes),
    )


_INTERNAL = {Category.SAVINGS, Category.TRANSFER}


def _round_up_100(value: Decimal) -> Decimal:
    return (value / 100).quantize(Decimal("1"), ROUND_UP) * 100


# --- 2 + 3. profile and direction ---------------------------------------------------------------
@dataclass(frozen=True)
class Answers:
    goal: Goal
    horizon: Horizon
    knowledge: Knowledge
    drop_reaction: Reaction


@dataclass(frozen=True)
class Direction:
    profile: ProfileName
    shares_percent: int
    bonds_percent: int
    headline: str
    explanation: str
    warnings: tuple[str, ...]
    suitable: bool  # False: investing does not fit this horizon; the customer may still go on


_HORIZON_POINTS = {"lt3": 0, "3to5": 1, "5to10": 2, "gt10": 3}
_REACTION_POINTS = {"sell_all": 0, "worried": 1, "wait": 2, "buy_more": 3}
_SPLIT: Mapping[ProfileName, int] = {"defensive": 30, "neutral": 60, "dynamic": 90}
_ORDER: tuple[ProfileName, ...] = ("defensive", "neutral", "dynamic")
_LABEL: Mapping[ProfileName, str] = {
    "defensive": "defensief",
    "neutral": "neutraal",
    "dynamic": "dynamisch",
}


def direction_for(answers: Answers) -> Direction:
    score = _HORIZON_POINTS[answers.horizon] + _REACTION_POINTS[answers.drop_reaction]
    profile: ProfileName = "defensive" if score <= 2 else "neutral" if score <= 4 else "dynamic"
    warnings: list[str] = []
    suitable = True

    cap: ProfileName = "dynamic"
    if answers.horizon == "lt3":
        cap, suitable = "defensive", False
        warnings.append(
            "Geld dat je binnen 3 jaar nodig hebt, beleg je beter niet: een daling heeft dan geen "
            "tijd om te herstellen. Sparen is hier de gezonde keuze."
        )
    elif answers.horizon == "3to5" or answers.goal == "purchase":
        cap = "neutral"
        if answers.goal == "purchase":
            warnings.append(
                "Voor een aankoop op een vaste datum (bv. een huis) is een rustiger mix "
                "verstandig: je wil niet moeten verkopen net na een daling."
            )
    if _ORDER.index(profile) > _ORDER.index(cap):
        profile = cap
    if answers.drop_reaction == "sell_all":
        warnings.append(
            "Je zegt dat je bij een daling alles zou verkopen. Dat is net het moment waarop "
            "beleggers het meest verliezen. Een defensieve mix schommelt minder."
        )
    if answers.knowledge == "none":
        warnings.append(
            "Nieuw in beleggen? Begin met één of twee brede ETF's en kleine maandelijkse stappen. "
            "Je adviseur legt het graag uit, zonder verplichtingen."
        )

    shares = _SPLIT[profile]
    return Direction(
        profile=profile,
        shares_percent=shares,
        bonds_percent=100 - shares,
        headline=f"Je profiel: {_LABEL[profile]} · ongeveer {shares}% aandelen, "
        f"{100 - shares}% obligaties",
        explanation=(
            "Aandelen groeien op lange termijn meestal het meest, maar schommelen sterk. "
            "Obligaties zijn rustiger en dempen dalingen. Hoe langer je horizon en hoe rustiger je "
            "blijft bij een daling, hoe meer aandelen passen. Kate wijst een richting aan; jij "
            "kiest de ETF's."
        ),
        warnings=tuple(warnings),
        suitable=suitable,
    )


# --- 4. the customer's mix -----------------------------------------------------------------------
FitTag = Literal["fits", "addition", "caution", "not_for_you"]


@dataclass(frozen=True)
class EtfFit:
    etf: Etf
    tag: FitTag
    note: str
    allowed: bool


def fit_for(etf: Etf, direction: Direction, knowledge: Knowledge) -> EtfFit:
    if etf.role == "complex":
        if knowledge == "none":
            return EtfFit(
                etf,
                "not_for_you",
                "Complex product. Zonder beleggingservaring kan je het niet kiezen.",
                False,
            )
        return EtfFit(etf, "not_for_you", "Complex hefboomproduct, niet om lang te houden.", True)
    if etf.role == "niche":
        return EtfFit(etf, "caution", "Eén sector: hooguit een klein deel (max. 10%).", True)
    if etf.role == "satellite":
        return EtfFit(etf, "addition", "Goede aanvulling in een kleine dosis (max. 20%).", True)
    if etf.asset_class == "bonds" and direction.bonds_percent < 20:
        return EtfFit(etf, "addition", "Kan, maar je profiel wijst naar weinig obligaties.", True)
    if etf.asset_class == "shares" and direction.shares_percent <= 30:
        return EtfFit(etf, "fits", "Brede basis; hou het aandelendeel wel beperkt.", True)
    return EtfFit(etf, "fits", "Brede, goedkope basis die past bij je profiel.", True)


@dataclass(frozen=True)
class MixCheck:
    shares_percent: int
    yearly_cost_percent: Decimal
    warnings: tuple[str, ...]
    blocked: tuple[str, ...]  # reasons the mix cannot be chosen at all

    @property
    def needs_acknowledgement(self) -> bool:
        return bool(self.warnings)


def check_mix(weights: Mapping[str, int], direction: Direction, knowledge: Knowledge) -> MixCheck:
    blocked: list[str] = []
    warnings: list[str] = []
    if not weights:
        blocked.append("Kies minstens één ETF.")
    if any(w <= 0 for w in weights.values()) or sum(weights.values()) != 100:
        blocked.append("De verdeling moet samen precies 100% zijn.")
    unknown = [etf_id for etf_id in weights if etf_id not in BY_ID]
    if unknown:
        blocked.append("Onbekende ETF gekozen.")
    if blocked:
        return MixCheck(0, Decimal(0), (), tuple(blocked))

    etfs = {etf_id: BY_ID[etf_id] for etf_id in weights}
    shares = sum(w for etf_id, w in weights.items() if etfs[etf_id].asset_class == "shares")
    cost = sum(
        (etfs[etf_id].ter_percent * w / 100 for etf_id, w in weights.items()), Decimal(0)
    ).quantize(Decimal("0.01"))

    for etf_id, weight in weights.items():
        fit = fit_for(etfs[etf_id], direction, knowledge)
        if not fit.allowed:
            blocked.append(f"{etfs[etf_id].name}: {fit.note}")
        elif etfs[etf_id].role == "complex":
            warnings.append(
                f"{etfs[etf_id].name} is een complex hefboomproduct: je kan veel verliezen, "
                "ook als de index stijgt."
            )
        elif etfs[etf_id].role == "niche" and weight > 10:
            warnings.append(f"{weight}% in één sector ({etfs[etf_id].index}) is veel.")
        elif etfs[etf_id].role == "satellite" and weight > 20:
            warnings.append(f"{weight}% in {etfs[etf_id].region} is meer dan een aanvulling.")
    if not any(etfs[etf_id].role == "core" for etf_id in weights):
        warnings.append("Je mix heeft geen brede basis (een wereld- of obligatie-ETF).")
    if abs(shares - direction.shares_percent) > 20:
        warnings.append(
            f"Je mix is {shares}% aandelen; je profiel wijst naar ongeveer "
            f"{direction.shares_percent}%."
        )
    if len(weights) > 5:
        warnings.append("Meer dan 5 ETF's voegt zelden spreiding toe, wel complexiteit.")
    return MixCheck(shares, cost, tuple(warnings), tuple(blocked))


def drop_example(amount: Decimal, shares_percent: int) -> Decimal:
    """What a 20% drop in shares (and 5% in bonds) would do to `amount`. Illustration only."""
    shares = amount * shares_percent / 100
    bonds = amount - shares
    return (shares * Decimal("0.80") + bonds * Decimal("0.95")).quantize(Decimal("1"))
