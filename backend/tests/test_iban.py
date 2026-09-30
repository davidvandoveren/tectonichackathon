import pytest

from app.domain.iban import is_valid_iban, make_be_iban


@pytest.mark.parametrize("iban", ["BE71096123456769", "BE71 0961 2345 6769", "be71096123456769"])
def test_valid_ibans(iban: str) -> None:
    assert is_valid_iban(iban)


@pytest.mark.parametrize("iban", ["BE72096123456769", "BE7109612345676", "", "XX00"])
def test_invalid_ibans(iban: str) -> None:
    assert not is_valid_iban(iban)


def test_generated_belgian_ibans_are_valid() -> None:
    assert all(is_valid_iban(make_be_iban(n)) for n in range(7_350_000_000, 7_350_000_050))
