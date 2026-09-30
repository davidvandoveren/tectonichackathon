"""Illustrative ETF catalogue for the demo.

The products are **fictitious** ("Demo …") and follow real, well-known indices, so the explanation
is realistic without presenting a real fund's numbers or prices as facts. Prices are simulated and
deterministic (see `price_on`), so every demo shows the same curve.
"""

import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

AssetClass = Literal["shares", "bonds"]
# core: a broad base that can carry a whole portfolio · satellite: a sensible addition in small
# doses · niche: one theme or sector, concentrated · complex: leveraged, not for buy-and-hold.
Role = Literal["core", "satellite", "niche", "complex"]

_EPOCH = date(2026, 1, 1)


@dataclass(frozen=True)
class Etf:
    id: str
    name: str
    index: str
    asset_class: AssetClass
    role: Role
    region: str
    ter_percent: Decimal  # yearly running cost
    risk_class: int  # SRI 1 (low) … 7 (high), as on the key information document
    distributing: bool
    holdings: int
    explanation: str
    # Simulation only: base price on 1 Jan 2026, yearly drift and wobble amplitude.
    base_price: Decimal
    drift: float
    wobble: float


CATALOG: tuple[Etf, ...] = (
    Etf(
        "etf_world",
        "Demo Wereld Aandelen ETF (kapitaliserend)",
        "MSCI World",
        "shares",
        "core",
        "23 ontwikkelde landen",
        Decimal("0.20"),
        4,
        False,
        1400,
        "Zo'n 1.400 grote en middelgrote bedrijven uit 23 ontwikkelde landen in één product. "
        "Breed gespreid, lage kosten: een klassieke basis voor wie lang belegt.",
        Decimal("100.00"),
        0.07,
        0.04,
    ),
    Etf(
        "etf_allworld",
        "Demo All-World Aandelen ETF (uitkerend)",
        "FTSE All-World",
        "shares",
        "core",
        "ontwikkelde + opkomende landen",
        Decimal("0.22"),
        4,
        True,
        4200,
        "Ruim 4.000 bedrijven wereldwijd, ook uit opkomende landen. Keert dividend uit: dat "
        "wordt belast (roerende voorheffing), dus netto hou je iets minder over dan bij "
        "kapitaliserend.",
        Decimal("110.00"),
        0.068,
        0.04,
    ),
    Etf(
        "etf_europe",
        "Demo Europa Aandelen ETF",
        "STOXX Europe 600",
        "shares",
        "satellite",
        "Europa",
        Decimal("0.20"),
        4,
        False,
        600,
        "600 Europese bedrijven. Een aanvulling als je Europa wat zwaarder wil laten wegen; "
        "wereld-ETF's bevatten Europa al.",
        Decimal("50.00"),
        0.055,
        0.045,
    ),
    Etf(
        "etf_em",
        "Demo Opkomende Markten ETF",
        "MSCI Emerging Markets",
        "shares",
        "satellite",
        "opkomende landen",
        Decimal("0.18"),
        5,
        False,
        1300,
        "Bedrijven uit o.a. China, India, Taiwan en Brazilië. Meer groeikansen, maar ook "
        "grotere schommelingen. Meestal een kleine aanvulling naast een wereld-ETF.",
        Decimal("30.00"),
        0.06,
        0.07,
    ),
    Etf(
        "etf_govbond",
        "Demo Euro Staatsobligaties ETF",
        "Bloomberg Euro Treasury",
        "bonds",
        "core",
        "eurozone",
        Decimal("0.09"),
        2,
        False,
        400,
        "Leningen aan eurolanden. Rustiger dan aandelen en een buffer als de beurs daalt, maar "
        "ook minder rendement. Let op: bij obligatie-ETF's kan bij verkoop Reynderstaks gelden.",
        Decimal("45.00"),
        0.025,
        0.015,
    ),
    Etf(
        "etf_aggbond",
        "Demo Wereld Obligaties ETF (EUR-afgedekt)",
        "Bloomberg Global Aggregate (EUR hedged)",
        "bonds",
        "core",
        "wereldwijd",
        Decimal("0.10"),
        2,
        False,
        9000,
        "Duizenden overheids- en bedrijfsobligaties wereldwijd, afgedekt tegen wisselkoersen. "
        "Een brede, rustige basis voor het defensieve deel.",
        Decimal("5.00"),
        0.028,
        0.015,
    ),
    Etf(
        "etf_clean",
        "Demo Schone Energie ETF",
        "S&P Global Clean Energy",
        "shares",
        "niche",
        "wereldwijd, één sector",
        Decimal("0.65"),
        6,
        False,
        100,
        "Een honderdtal bedrijven uit één sector. Kan sterk stijgen, maar ook jaren sterk dalen: "
        "weinig spreiding en hogere kosten. Hooguit een klein deel van je portefeuille.",
        Decimal("12.00"),
        0.04,
        0.12,
    ),
    Etf(
        "etf_lev",
        "Demo Nasdaq-100 3x Hefboom",
        "Nasdaq-100 (dagelijks 3x)",
        "shares",
        "complex",
        "VS, technologie",
        Decimal("0.75"),
        7,
        False,
        100,
        "Complex product: probeert elke dag drie keer de beweging van de index te volgen. Over "
        "langere tijd kan je veel verliezen, zelfs als de index stijgt. Niet bedoeld om lang te "
        "houden.",
        Decimal("40.00"),
        0.03,
        0.25,
    ),
)

BY_ID = {etf.id: etf for etf in CATALOG}

#: Belgian stock exchange tax on buying most EEA-registered ETFs (illustrative for the demo).
TOB_RATE = Decimal("0.0012")


def price_on(etf: Etf, day: date) -> Decimal:
    """Simulated price: a steady drift plus a deterministic wobble. Never a real quote."""
    t = (day - _EPOCH).days
    seed = sum(ord(c) for c in etf.id)
    growth = (1 + etf.drift) ** (t / 365)
    wobble = 1 + etf.wobble * math.sin(t / 23 + seed) * 0.5
    value = Decimal(str(float(etf.base_price) * growth * wobble))
    return value.quantize(Decimal("0.01"), ROUND_HALF_UP)
