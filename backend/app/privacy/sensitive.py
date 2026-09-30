"""The one list of sensitive spending (GDPR art. 9-style categories).

Health, religion, politics, trade-union membership and sex life/dating: such payments are never
labelled, profiled, turned into a moment or a product pitch, and never shown to anyone but the
customer. When in doubt a payment counts as sensitive: a false positive only means Kate stays
quiet, a false negative can hurt someone.
"""

import re

from app.domain.models import Transaction

#: Matched anywhere in the counterparty or description (lower-case).
SENSITIVE_KEYWORDS: tuple[str, ...] = (
    # health
    "apotheek",
    "pharmacie",
    "pharmacy",
    "psycholoog",
    "psychiater",
    "psychotherap",
    "therapeut",
    "ziekenhuis",
    "hôpital",
    "hospitalisatie",
    "dokter",
    "huisarts",
    "tandarts",
    "kinesist",
    "kliniek",
    "mutualiteit",
    "ziekenfonds",
    "cm-mc",
    "headspace",
    "meditatie",
    # religion
    "kerk",
    "moskee",
    "synagoge",
    "parochie",
    "église",
    # politics
    "partij",
    "vlaams belang",
    # trade union
    "vakbond",
    # dating / sex life
    "tinder",
    "bumble",
    "grindr",
    "dating",
)
#: Short acronyms only count as a whole word ("ACV Vakbond", not "Vacv…").
SENSITIVE_WORDS: tuple[str, ...] = ("acv", "abvv", "aclvb", "acod", "n-va", "pvda")

NEUTRAL_LABEL = "Overige uitgave"

_WORDS = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(w) for w in SENSITIVE_WORDS) + r")(?![\w-])"
)


def is_sensitive_text(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in SENSITIVE_KEYWORDS) or bool(_WORDS.search(lower))


def is_sensitive(transaction: Transaction) -> bool:
    return is_sensitive_text(f"{transaction.counterparty} {transaction.description}")
