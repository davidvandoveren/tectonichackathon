from decimal import Decimal

from app.domain.bank import TransferRequest
from app.domain.models import Account, AccountType
from app.skills.base import SkillContext


def own_account(ctx: SkillContext, kind: AccountType) -> Account | None:
    return next((a for a in ctx.bank.accounts_for(ctx.owner_id) if a.type == kind), None)


def move_between_own(
    ctx: SkillContext, source: AccountType, target: AccountType, amount: Decimal, text: str
) -> None:
    """Move money between two of the customer's own accounts, via the normal validated path."""
    src = own_account(ctx, source)
    dst = own_account(ctx, target)
    if src is None or dst is None:
        raise LookupError("account not found")
    ctx.bank.transfer(
        ctx.owner_id,
        TransferRequest(
            from_account_id=src.id,
            to_iban=dst.iban,
            to_name=dst.name,
            amount=amount,
            description=text,
        ),
        ctx.today,
    )
