"""Links between customers, what each side shares, and shared pots.

Every rule that decides who may see or do what lives in this module, so the router cannot forget
one. The rules (see `docs/ideas.md`, "Family circle"):

- A link exists only after **both** sides said yes. It is never inferred from transactions.
- Each side decides what *it* shares with the other (`Level`), default the minimum. Nobody can
  raise what the other side shares.
- Either side can end a link at any time, without the other being able to block it.
- Guardianship over a minor is not something you can claim with an invite: it comes from the
  (here: synthetic) civil registry, and it ends automatically on the child's 18th birthday. From
  then on the child decides what the parent may still see.
- Unknown and not-allowed look the same to the caller (`None` → 404), so the API cannot be used to
  find out who is a customer or who is linked to whom.

In memory, like `Bank`. Swap for a real store together with it.
"""

import secrets
import threading
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.bank import Bank, TransferRequest
from app.domain.iban import make_be_iban
from app.domain.models import Account, User

ADULT_AGE = 18
MAX_PENDING_INVITES = 10
MAX_POTS_PER_OWNER = 10
# Pots get IBANs from their own synthetic range, far away from the seeded accounts.
_POT_IBAN_BASE = 9_100_000_000


class Level(StrEnum):
    """What one side of a link shares with the other. Ordered: each level includes the previous."""

    EXISTS = "exists"  # the other only sees that the link exists
    GIFT = "gift"  # ... and may contribute to pots you share with them (sees progress only)
    POT = "pot"  # ... and sees who contributed what to those pots
    BALANCES = "balances"  # ... and sees your account balances (read-only, never transactions)

    @property
    def rank(self) -> int:
        return _LEVEL_ORDER.index(self)

    def at_least(self, other: "Level") -> bool:
        return self.rank >= other.rank


_LEVEL_ORDER = (Level.EXISTS, Level.GIFT, Level.POT, Level.BALANCES)


class Role(StrEnum):
    PARTNER = "partner"
    PARENT = "parent"
    CHILD = "child"
    GRANDPARENT = "grandparent"
    GRANDCHILD = "grandchild"
    GODPARENT = "godparent"
    GODCHILD = "godchild"
    SIBLING = "sibling"
    OTHER = "other"

    @property
    def counterpart(self) -> "Role":
        return _COUNTERPART.get(self, self)


_COUNTERPART = {
    Role.PARENT: Role.CHILD,
    Role.CHILD: Role.PARENT,
    Role.GRANDPARENT: Role.GRANDCHILD,
    Role.GRANDCHILD: Role.GRANDPARENT,
    Role.GODPARENT: Role.GODCHILD,
    Role.GODCHILD: Role.GODPARENT,
}


class Status(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"


class CircleError(Exception):
    """Well-formed but not allowed by the circle's rules (answered with 409/422, not 404)."""


@dataclass
class Link:
    id: str
    inviter_id: str
    # None when the invite went to a username that is not a customer (or cannot be invited). The
    # invite is kept anyway so the inviter's view is identical either way: no enumeration.
    invitee_id: str | None
    invitee_label: str
    roles: dict[str, Role]
    shares: dict[str, Level]
    status: Status
    created_on: date
    accepted_on: date | None = None
    ended_on: date | None = None
    # Legal guardianship over a minor, from the civil registry, never from an invite.
    guardian_id: str | None = None
    ward_id: str | None = None
    # The ward explicitly chose what to share after turning 18 (until then Kate asks).
    ward_decided: bool = False

    def has_member(self, user_id: str) -> bool:
        return user_id in (self.inviter_id, self.invitee_id)

    def other(self, user_id: str) -> str | None:
        return self.invitee_id if user_id == self.inviter_id else self.inviter_id


@dataclass(frozen=True)
class Contribution:
    user_id: str
    amount: Decimal
    booked_on: date
    note: str


@dataclass
class Pot:
    id: str
    owner_id: str
    name: str
    goal: Decimal | None
    iban: str
    created_on: date
    member_ids: set[str] = field(default_factory=set)
    balance: Decimal = Decimal("0.00")
    contributions: list[Contribution] = field(default_factory=list)


def age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def eighteenth_birthday(birth: date) -> date:
    try:
        return birth.replace(year=birth.year + ADULT_AGE)
    except ValueError:  # born on 29 February
        return date(birth.year + ADULT_AGE, 3, 1)


class FamilyCircle:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank
        self._links: dict[str, Link] = {}
        self._pots: dict[str, Pot] = {}
        self._birth_dates: dict[str, date] = {}
        self._pot_counter = 0
        self._lock = threading.Lock()

    # --- people --------------------------------------------------------------------------------
    def set_birth_date(self, user_id: str, birth: date) -> None:
        self._birth_dates[user_id] = birth

    def birth_date(self, user_id: str) -> date | None:
        return self._birth_dates.get(user_id)

    def is_minor(self, user_id: str, today: date) -> bool:
        birth = self._birth_dates.get(user_id)
        return birth is not None and age_on(birth, today) < ADULT_AGE

    # --- links: reads --------------------------------------------------------------------------
    def links_for(self, user_id: str) -> list[Link]:
        """Pending and active links the user is part of (ended ones are gone for both sides)."""
        return sorted(
            (
                link
                for link in self._links.values()
                if link.has_member(user_id) and link.status != Status.ENDED
            ),
            key=lambda link: (link.status != Status.ACTIVE, link.created_on, link.id),
        )

    def link_for(self, user_id: str, link_id: str) -> Link | None:
        link = self._links.get(link_id)
        if link is None or not link.has_member(user_id) or link.status == Status.ENDED:
            return None
        return link

    def active_link_between(self, a: str, b: str) -> Link | None:
        return next(
            (
                link
                for link in self._links.values()
                if link.status == Status.ACTIVE and link.has_member(a) and link.has_member(b)
            ),
            None,
        )

    def guardianship_active(self, link: Link, today: date) -> bool:
        return link.ward_id is not None and self.is_minor(link.ward_id, today)

    def effective_share(self, link: Link, from_id: str, today: date) -> Level:
        """What `from_id` shares with the other member today.

        A minor cannot hide their accounts from their legal guardian: the guardian has legal
        authority until the 18th birthday. After that, only the child's own choice counts.
        """
        if link.status != Status.ACTIVE:
            return Level.EXISTS
        if from_id == link.ward_id and self.guardianship_active(link, today):
            return Level.BALANCES
        return link.shares.get(from_id, Level.EXISTS)

    def shared_accounts(self, viewer_id: str, link_id: str, today: date) -> list[Account] | None:
        """The other member's accounts, only if they share `balances` with the viewer."""
        link = self.link_for(viewer_id, link_id)
        if link is None or link.status != Status.ACTIVE:
            return None
        other = link.other(viewer_id)
        if other is None or not self.effective_share(link, other, today).at_least(Level.BALANCES):
            return None
        return self._bank.accounts_for(other)

    # --- links: writes -------------------------------------------------------------------------
    def invite(self, inviter: User, username: str, role: Role, share: Level, today: date) -> Link:
        """Invite someone. The result looks the same whether or not `username` is a customer."""
        if self.is_minor(inviter.id, today):
            raise CircleError("Vanaf 18 jaar kan je zelf mensen uitnodigen")
        with self._lock:
            outgoing = [
                link
                for link in self._links.values()
                if link.inviter_id == inviter.id and link.status == Status.PENDING
            ]
            if len(outgoing) >= MAX_PENDING_INVITES:
                raise CircleError("Te veel openstaande uitnodigingen")
            invitee = self._bank.find_user_by_username(username)
            # Nobody can be invited while under 18 (only the registry links minors), and a pair
            # has at most one link. Either way the inviter gets the same answer.
            reachable = (
                invitee is not None
                and invitee.id != inviter.id
                and not self.is_minor(invitee.id, today)
                and self._open_link_between(inviter.id, invitee.id) is None
            )
            invitee_id = invitee.id if reachable and invitee is not None else None
            link = Link(
                id=_new_id("fl"),
                inviter_id=inviter.id,
                invitee_id=invitee_id,
                invitee_label=username,
                roles={inviter.id: role, **({invitee_id: role.counterpart} if invitee_id else {})},
                shares={inviter.id: share, **({invitee_id: Level.EXISTS} if invitee_id else {})},
                status=Status.PENDING,
                created_on=today,
            )
            self._links[link.id] = link
            return link

    def accept(self, user_id: str, link_id: str, share: Level, today: date) -> Link | None:
        with self._lock:
            link = self.link_for(user_id, link_id)
            if link is None or link.invitee_id != user_id:
                return None
            if link.status != Status.PENDING:
                raise CircleError("Deze uitnodiging is al beantwoord")
            link.status = Status.ACTIVE
            link.accepted_on = today
            link.shares[user_id] = share
            return link

    def end(self, user_id: str, link_id: str, today: date) -> Link | None:
        """Decline, cancel or end. Either side can, and the other side cannot stop it."""
        with self._lock:
            link = self.link_for(user_id, link_id)
            if link is None:
                return None
            if self.guardianship_active(link, today):
                raise CircleError(
                    "Wettelijke voogdij kan je niet in de app stopzetten; ze stopt automatisch "
                    "op de 18de verjaardag"
                )
            link.status = Status.ENDED
            link.ended_on = today
            # Pots shared through this link are no longer visible to the other side.
            for pot in self._pots.values():
                if pot.owner_id in (link.inviter_id, link.invitee_id):
                    pot.member_ids -= {link.inviter_id, link.invitee_id} - {pot.owner_id}
            return link

    def set_share(self, user_id: str, link_id: str, share: Level) -> Link | None:
        """Change what *you* share. Never touches what the other side shares."""
        with self._lock:
            link = self.link_for(user_id, link_id)
            if link is None or link.status != Status.ACTIVE:
                return None
            link.shares[user_id] = share
            if user_id == link.ward_id:
                link.ward_decided = True
            return link

    def add_registry_guardianship(
        self, guardian_id: str, ward_id: str, since: date, guardian_share: Level = Level.EXISTS
    ) -> Link:
        """Seed-only: a parent-child link as the civil registry knows it. Not reachable via API."""
        link = Link(
            id=_new_id("fl"),
            inviter_id=guardian_id,
            invitee_id=ward_id,
            invitee_label="",
            roles={guardian_id: Role.PARENT, ward_id: Role.CHILD},
            shares={guardian_id: guardian_share, ward_id: Level.EXISTS},
            status=Status.ACTIVE,
            created_on=since,
            accepted_on=since,
            guardian_id=guardian_id,
            ward_id=ward_id,
        )
        self._links[link.id] = link
        return link

    def _open_link_between(self, a: str, b: str) -> Link | None:
        return next(
            (
                link
                for link in self._links.values()
                if link.status != Status.ENDED and link.has_member(a) and link.has_member(b)
            ),
            None,
        )

    # --- pots ----------------------------------------------------------------------------------
    def pot_level(self, user_id: str, pot: Pot, today: date) -> Level | None:
        """How much of the pot `user_id` may see. `None` = nothing, not even that it exists."""
        if pot.owner_id == user_id:
            return Level.BALANCES
        if user_id not in pot.member_ids:
            return None
        link = self.active_link_between(pot.owner_id, user_id)
        if link is None:
            return None
        share = self.effective_share(link, pot.owner_id, today)
        if not share.at_least(Level.GIFT):
            return None
        return Level.POT if share.at_least(Level.POT) else Level.GIFT

    def pots_for(self, user_id: str, today: date) -> list[tuple[Pot, Level]]:
        visible = []
        for pot in self._pots.values():
            level = self.pot_level(user_id, pot, today)
            if level is not None:
                visible.append((pot, level))
        return sorted(visible, key=lambda item: (item[0].owner_id != user_id, item[0].created_on))

    def pot_for(self, user_id: str, pot_id: str, today: date) -> tuple[Pot, Level] | None:
        pot = self._pots.get(pot_id)
        if pot is None:
            return None
        level = self.pot_level(user_id, pot, today)
        return (pot, level) if level is not None else None

    def create_pot(
        self,
        owner_id: str,
        name: str,
        goal: Decimal | None,
        member_link_ids: list[str],
        today: date,
    ) -> Pot | None:
        """`None` if any link is unknown or not the owner's active link (404, no enumeration)."""
        with self._lock:
            members = set()
            for link_id in member_link_ids:
                link = self.link_for(owner_id, link_id)
                other = link.other(owner_id) if link is not None else None
                if link is None or link.status != Status.ACTIVE or other is None:
                    return None
                members.add(other)
            if sum(1 for p in self._pots.values() if p.owner_id == owner_id) >= MAX_POTS_PER_OWNER:
                raise CircleError("Je hebt al het maximum aantal potjes")
            self._pot_counter += 1
            pot = Pot(
                id=_new_id("fp"),
                owner_id=owner_id,
                name=name,
                goal=goal,
                iban=make_be_iban(_POT_IBAN_BASE + self._pot_counter),
                created_on=today,
                member_ids=members,
            )
            self._pots[pot.id] = pot
            return pot

    def contribute(
        self,
        user: User,
        pot_id: str,
        from_account_id: str,
        amount: Decimal,
        note: str,
        today: date,
    ) -> Contribution | None:
        """Move the user's *own* money into a pot they may contribute to.

        Uses the ordinary, server-validated transfer (own account only, no credit card, enough
        funds), so the circle adds no new way to move money.
        """
        found = self.pot_for(user.id, pot_id, today)
        if found is None:
            return None
        pot, _ = found
        request = TransferRequest(
            from_account_id=from_account_id,
            to_iban=pot.iban,
            to_name=f"Potje {pot.name}",
            amount=amount,
            description=note or f"Bijdrage potje {pot.name}",
        )
        # LookupError / TransferError propagate: the router maps them like /transfers does.
        self._bank.transfer(user.id, request, today)
        with self._lock:
            contribution = Contribution(user.id, amount, today, note)
            pot.balance += amount
            pot.contributions.append(contribution)
            return contribution

    def seed_pot_contribution(self, pot: Pot, contribution: Contribution) -> None:
        """Seed-only: history that happened before the demo started."""
        pot.balance += contribution.amount
        pot.contributions.append(contribution)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"
