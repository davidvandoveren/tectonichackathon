"""Family circle for the logged-in customer: links, what each side shares, and shared pots.

All authorization lives in `app.family.circle`; this router only translates. `None` from the
circle means "unknown or not yours" and becomes the same 404 everywhere, so nobody can use these
endpoints to learn who is a customer or who is linked to whom.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import Field, field_validator

from app.dependencies import BankDep, CurrentUser, TodayDep
from app.domain.bank import Bank, TransferError
from app.domain.models import AccountType, User
from app.family.circle import (
    CircleError,
    FamilyCircle,
    Level,
    Link,
    Pot,
    Role,
    Status,
    eighteenth_birthday,
)
from app.family.suggestions import suggestions_for
from app.schemas import MAX_TRANSFER, ApiModel, Money

router = APIRouter(prefix="/family", tags=["family"])

_NOT_FOUND = "Not found"
LinkId = Annotated[str, Path(pattern=r"^fl_[0-9a-f]{12}$")]
PotId = Annotated[str, Path(pattern=r"^fp_[0-9a-f]{12}$")]


def get_circle(request: Request) -> FamilyCircle:
    circle: FamilyCircle = request.app.state.family
    return circle


CircleDep = Annotated[FamilyCircle, Depends(get_circle)]


def _clean(value: str) -> str:
    cleaned = " ".join(value.split())
    if any(not char.isprintable() for char in cleaned):
        raise ValueError("Contains control characters")
    return cleaned


# --- shapes --------------------------------------------------------------------------------------
class GuardianshipOut(ApiModel):
    my_side: Literal["guardian", "ward"]
    active: bool
    ends_on: date


class LinkOut(ApiModel):
    id: str
    status: Literal["pending", "active"]
    direction: Literal["incoming", "outgoing"] | None
    other_name: str
    my_role: Role
    their_role: Role
    i_share: Level
    they_share: Level
    guardianship: GuardianshipOut | None
    can_end: bool
    can_view_accounts: bool
    since: date


class ContributionOut(ApiModel):
    name: str
    amount: Money
    booked_on: date
    mine: bool


class PotOut(ApiModel):
    id: str
    name: str
    goal: Money | None
    balance: Money
    progress_percent: int | None
    owner_name: str
    mine: bool
    access: Literal["owner", "pot", "gift"]
    # Only for the owner and for `pot` access; `gift` only sees progress and its own gifts.
    members: list[str] | None
    contributions: list[ContributionOut]


class SuggestionOut(ApiModel):
    id: str
    kind: str
    title: str
    body: str
    reason: str
    cta_label: str
    cta_target: str


class MeOut(ApiModel):
    minor: bool
    adult_on: date | None


class FamilyOut(ApiModel):
    me: MeOut
    links: list[LinkOut]
    pots: list[PotOut]
    suggestions: list[SuggestionOut]


class InviteIn(ApiModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    my_role: Role
    share: Level = Level.EXISTS


class InviteOut(ApiModel):
    message: str
    link: LinkOut


class ShareIn(ApiModel):
    share: Level


class SharedAccountOut(ApiModel):
    name: str
    type: AccountType
    balance: Money
    currency: str


class PotIn(ApiModel):
    name: str = Field(min_length=1, max_length=40)
    goal: Decimal | None = Field(default=None, gt=0, le=Decimal(100_000), decimal_places=2)
    member_link_ids: list[Annotated[str, Field(pattern=r"^fl_[0-9a-f]{12}$")]] = Field(
        default_factory=list, max_length=10
    )

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return _clean(value)


class ContributionIn(ApiModel):
    from_account_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, le=MAX_TRANSFER, max_digits=7, decimal_places=2)
    note: str = Field(default="", max_length=140)

    @field_validator("note")
    @classmethod
    def _clean_note(cls, value: str) -> str:
        return _clean(value)


# --- mapping -------------------------------------------------------------------------------------
def _name(bank: Bank, user_id: str | None) -> str:
    user = bank.get_user(user_id) if user_id else None
    return f"{user.first_name} {user.last_name}" if user else ""


def _link_out(link: Link, me: User, circle: FamilyCircle, bank: Bank, today: date) -> LinkOut:
    other = link.other(me.id)
    my_role = link.roles[me.id]
    direction: Literal["incoming", "outgoing"] | None = None
    if link.status == Status.PENDING:
        direction = "outgoing" if link.inviter_id == me.id else "incoming"
    guardianship = None
    if link.ward_id is not None:
        birth = circle.birth_date(link.ward_id)
        guardianship = GuardianshipOut(
            my_side="guardian" if me.id == link.guardian_id else "ward",
            active=circle.guardianship_active(link, today),
            ends_on=eighteenth_birthday(birth) if birth else today,
        )
    they_share = circle.effective_share(link, other, today) if other is not None else Level.EXISTS
    return LinkOut(
        id=link.id,
        status="active" if link.status == Status.ACTIVE else "pending",
        direction=direction,
        # An outgoing invite only ever shows what the inviter typed: never whether it exists.
        other_name=link.invitee_label if direction == "outgoing" else _name(bank, other),
        my_role=my_role,
        their_role=link.roles.get(other, my_role.counterpart) if other else my_role.counterpart,
        i_share=circle.effective_share(link, me.id, today)
        if link.status == Status.ACTIVE
        else link.shares.get(me.id, Level.EXISTS),
        they_share=they_share,
        guardianship=guardianship,
        can_end=not circle.guardianship_active(link, today),
        can_view_accounts=link.status == Status.ACTIVE and they_share.at_least(Level.BALANCES),
        since=link.accepted_on or link.created_on,
    )


def _pot_out(pot: Pot, level: Level, me: User, bank: Bank) -> PotOut:
    mine = pot.owner_id == me.id
    detailed = mine or level.at_least(Level.POT)
    contributions = [
        ContributionOut(
            name=_name(bank, c.user_id),
            amount=c.amount,
            booked_on=c.booked_on,
            mine=c.user_id == me.id,
        )
        for c in sorted(pot.contributions, key=lambda c: c.booked_on, reverse=True)
        if detailed or c.user_id == me.id
    ]
    return PotOut(
        id=pot.id,
        name=pot.name,
        goal=pot.goal,
        balance=pot.balance,
        progress_percent=min(100, int(pot.balance * 100 / pot.goal)) if pot.goal else None,
        owner_name=_name(bank, pot.owner_id),
        mine=mine,
        access="owner" if mine else ("pot" if level.at_least(Level.POT) else "gift"),
        members=sorted(_name(bank, m) for m in pot.member_ids) if detailed else None,
        contributions=contributions,
    )


def _conflict(exc: CircleError) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


# --- endpoints -----------------------------------------------------------------------------------
@router.get("", response_model=FamilyOut)
def family_overview(
    user: CurrentUser, bank: BankDep, circle: CircleDep, today: TodayDep
) -> FamilyOut:
    birth = circle.birth_date(user.id)
    minor = circle.is_minor(user.id, today)
    return FamilyOut(
        me=MeOut(minor=minor, adult_on=eighteenth_birthday(birth) if birth and minor else None),
        links=[_link_out(link, user, circle, bank, today) for link in circle.links_for(user.id)],
        pots=[_pot_out(pot, level, user, bank) for pot, level in circle.pots_for(user.id, today)],
        suggestions=[
            SuggestionOut.model_validate(s, from_attributes=True)
            for s in suggestions_for(user.id, circle, bank, today)
        ],
    )


@router.post("/invites", response_model=InviteOut, status_code=status.HTTP_202_ACCEPTED)
def invite(
    body: InviteIn, user: CurrentUser, bank: BankDep, circle: CircleDep, today: TodayDep
) -> InviteOut:
    try:
        link = circle.invite(user, body.username, body.my_role, body.share, today)
    except CircleError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return InviteOut(
        # Same text whether or not the username is a customer who can be invited.
        message="Als deze persoon een KBC-klant is die je kan uitnodigen, ziet die je uitnodiging "
        "in de app. Pas als die ja zegt, zijn jullie gekoppeld.",
        link=_link_out(link, user, circle, bank, today),
    )


@router.post("/links/{link_id}/accept", response_model=LinkOut)
def accept(
    link_id: LinkId,
    body: ShareIn,
    user: CurrentUser,
    bank: BankDep,
    circle: CircleDep,
    today: TodayDep,
) -> LinkOut:
    try:
        link = circle.accept(user.id, link_id, body.share, today)
    except CircleError as exc:
        raise _conflict(exc) from exc
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return _link_out(link, user, circle, bank, today)


@router.post("/links/{link_id}/end", status_code=status.HTTP_204_NO_CONTENT)
def end(link_id: LinkId, user: CurrentUser, circle: CircleDep, today: TodayDep) -> None:
    """Decline an invite, cancel your own, or end a link. The other side cannot block it."""
    try:
        link = circle.end(user.id, link_id, today)
    except CircleError as exc:
        raise _conflict(exc) from exc
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)


@router.post("/links/{link_id}/sharing", response_model=LinkOut)
def set_sharing(
    link_id: LinkId,
    body: ShareIn,
    user: CurrentUser,
    bank: BankDep,
    circle: CircleDep,
    today: TodayDep,
) -> LinkOut:
    """Change what *you* share with the other side. There is no way to change what they share."""
    link = circle.set_share(user.id, link_id, body.share)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return _link_out(link, user, circle, bank, today)


@router.get("/links/{link_id}/accounts", response_model=list[SharedAccountOut])
def shared_accounts(
    link_id: LinkId, user: CurrentUser, circle: CircleDep, today: TodayDep
) -> list[SharedAccountOut]:
    """Balances the other side shares with you. Never transactions, never IBANs."""
    accounts = circle.shared_accounts(user.id, link_id, today)
    if accounts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return [SharedAccountOut.model_validate(a, from_attributes=True) for a in accounts]


@router.post("/pots", response_model=PotOut, status_code=status.HTTP_201_CREATED)
def create_pot(
    body: PotIn, user: CurrentUser, bank: BankDep, circle: CircleDep, today: TodayDep
) -> PotOut:
    if circle.is_minor(user.id, today):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Vanaf 18 jaar kan je zelf potjes delen"
        )
    try:
        pot = circle.create_pot(user.id, body.name, body.goal, body.member_link_ids, today)
    except CircleError as exc:
        raise _conflict(exc) from exc
    if pot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return _pot_out(pot, Level.BALANCES, user, bank)


@router.post(
    "/pots/{pot_id}/contributions", response_model=PotOut, status_code=status.HTTP_201_CREATED
)
def contribute(
    pot_id: PotId,
    body: ContributionIn,
    user: CurrentUser,
    bank: BankDep,
    circle: CircleDep,
    today: TodayDep,
) -> PotOut:
    try:
        contribution = circle.contribute(
            user, pot_id, body.from_account_id, body.amount, body.note, today
        )
    except LookupError as exc:  # not the caller's account: same answer as /transfers
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND) from exc
    except TransferError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if contribution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    found = circle.pot_for(user.id, pot_id, today)
    if found is None:  # pragma: no cover - access was just checked
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return _pot_out(found[0], found[1], user, bank)
