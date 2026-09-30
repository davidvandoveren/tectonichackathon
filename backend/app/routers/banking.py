from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import BankDep, CurrentUser, KateStateDep, TodayDep
from app.domain.bank import TransferError, TransferRequest
from app.schemas import AccountOut, InsightOut, TransactionOut, TransferIn
from app.services.insights import insights_for

router = APIRouter(tags=["banking"])

# Same message whether the account does not exist or belongs to someone else (no enumeration).
_NOT_FOUND = "Account not found"


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(user: CurrentUser, bank: BankDep) -> list[AccountOut]:
    return [AccountOut.model_validate(a) for a in bank.accounts_for(user.id)]


@router.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(account_id: str, user: CurrentUser, bank: BankDep) -> AccountOut:
    account = bank.account_for(user.id, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return AccountOut.model_validate(account)


@router.get("/accounts/{account_id}/transactions", response_model=list[TransactionOut])
def list_transactions(
    account_id: str,
    user: CurrentUser,
    bank: BankDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[TransactionOut]:
    if bank.account_for(user.id, account_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return [
        TransactionOut.model_validate(t) for t in bank.transactions_for(user.id, account_id, limit)
    ]


@router.post("/transfers", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transfer(
    body: TransferIn, user: CurrentUser, bank: BankDep, today: TodayDep
) -> TransactionOut:
    request = TransferRequest(
        from_account_id=body.from_account_id,
        to_iban=body.to_iban,
        to_name=body.to_name,
        amount=body.amount,
        description=body.description,
    )
    try:
        transaction = bank.transfer(user.id, request, today)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND) from exc
    except TransferError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return TransactionOut.model_validate(transaction)


@router.get("/insights", response_model=list[InsightOut])
def list_insights(
    user: CurrentUser, bank: BankDep, state: KateStateDep, today: TodayDep
) -> list[InsightOut]:
    return [InsightOut.model_validate(i) for i in insights_for(bank, user, today, state)]
