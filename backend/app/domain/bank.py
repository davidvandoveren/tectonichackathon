import secrets
import threading
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.iban import normalize_iban
from app.domain.models import Account, AccountType, Category, Transaction, User

# Per-transfer ceiling. The API schema enforces it too; the bank re-checks so that every caller
# (API, Kate Skills, scripts) is held to the same rule.
MAX_TRANSFER = Decimal("10000.00")


class TransferError(Exception):
    """A transfer that is well-formed but not allowed by business rules."""


@dataclass(frozen=True)
class TransferRequest:
    from_account_id: str
    to_iban: str
    to_name: str
    amount: Decimal
    description: str


class Bank:
    """In-memory data store with ownership-scoped queries.

    Every read or write of customer data takes the *authenticated* user's id and only ever returns
    that user's data. Callers cannot ask for "account X" without also proving whose it is, which
    rules out IDOR by construction. Swap this class for a Firestore/Cloud SQL implementation later.
    """

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._accounts: dict[str, Account] = {}
        self._transactions: list[Transaction] = []
        self._lock = threading.Lock()

    # --- seeding -------------------------------------------------------------------------------
    def add_user(self, user: User) -> None:
        self._users[user.id] = user

    def add_account(self, account: Account) -> None:
        self._accounts[account.id] = account

    def add_transaction(self, transaction: Transaction) -> None:
        self._transactions.append(transaction)

    # --- users ---------------------------------------------------------------------------------
    def list_users(self) -> list[User]:
        return list(self._users.values())

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def find_user_by_username(self, username: str) -> User | None:
        return next((u for u in self._users.values() if u.username == username), None)

    # --- owner-scoped reads --------------------------------------------------------------------
    def accounts_for(self, owner_id: str) -> list[Account]:
        return [a for a in self._accounts.values() if a.owner_id == owner_id]

    def account_for(self, owner_id: str, account_id: str) -> Account | None:
        account = self._accounts.get(account_id)
        return account if account is not None and account.owner_id == owner_id else None

    def transactions_for(self, owner_id: str, account_id: str, limit: int) -> list[Transaction]:
        if self.account_for(owner_id, account_id) is None:
            return []
        own = [t for t in self._transactions if t.account_id == account_id]
        return sorted(own, key=lambda t: t.booked_at, reverse=True)[:limit]

    def all_transactions_for(self, owner_id: str) -> list[Transaction]:
        own_ids = {a.id for a in self.accounts_for(owner_id)}
        return [t for t in self._transactions if t.account_id in own_ids]

    # --- owner-scoped writes -------------------------------------------------------------------
    def transfer(self, owner_id: str, request: TransferRequest, today: date) -> Transaction:
        amount = request.amount
        if not amount.is_finite() or amount <= 0 or amount > MAX_TRANSFER:
            raise TransferError("Invalid amount")
        if amount != amount.quantize(Decimal("0.01")):
            raise TransferError("Amount has more than 2 decimals")
        to_iban = normalize_iban(request.to_iban)
        with self._lock:
            source = self.account_for(owner_id, request.from_account_id)
            if source is None:
                raise LookupError("account not found")
            if source.type == AccountType.CREDIT_CARD:
                raise TransferError("Transfers from a credit card are not allowed")
            if source.iban == to_iban:
                raise TransferError("Source and destination account are the same")
            if request.amount > source.balance:
                raise TransferError("Insufficient funds")

            source.balance -= request.amount
            debit = Transaction(
                id=_new_id("t"),
                account_id=source.id,
                booked_at=today,
                description=request.description or f"Overschrijving naar {request.to_name}",
                counterparty=request.to_name,
                amount=-request.amount,
                category=Category.TRANSFER,
            )
            self._transactions.append(debit)

            destination = next((a for a in self._accounts.values() if a.iban == to_iban), None)
            if destination is not None:
                destination.balance += request.amount
                sender = self._users[owner_id]
                self._transactions.append(
                    Transaction(
                        id=_new_id("t"),
                        account_id=destination.id,
                        booked_at=today,
                        description=request.description or "Overschrijving",
                        counterparty=f"{sender.first_name} {sender.last_name}",
                        amount=request.amount,
                        category=Category.TRANSFER,
                    )
                )
            return debit


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"
