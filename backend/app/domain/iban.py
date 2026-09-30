import re

_IBAN_SHAPE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")


def normalize_iban(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def _mod97(iban: str) -> int:
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(char, 36)) for char in rearranged)
    return int(digits) % 97


def is_valid_iban(value: str) -> bool:
    iban = normalize_iban(value)
    return bool(_IBAN_SHAPE.match(iban)) and _mod97(iban) == 1


def format_iban(iban: str) -> str:
    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))


def make_be_iban(account_number: int) -> str:
    """Build a valid Belgian IBAN from a 10-digit account number (for synthetic data)."""
    base = f"{account_number:010d}"
    national_check = int(base) % 97 or 97
    bban = f"{base}{national_check:02d}"
    check = 98 - _mod97(f"BE00{bban}")
    return f"BE{check:02d}{bban}"
