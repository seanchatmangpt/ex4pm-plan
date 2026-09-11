# Copyright (c) AIRBUS and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Economic-action identities for planning without conflating SELECT with DO.

This module projects the canonical ex4pm economic byte ABI into planning space.
The byte identifies only the economic verb. Grounded objects/parameters,
provenance, value and authority remain external facts.

The projection is intentionally planner-neutral:

* HDDL can use :func:`hddl_action_symbol` as the stable primitive-action name.
* FOND can use :class:`FondTransitionRelation` plus :class:`FondPolicy` to
  represent nondeterministic successor sets and policy selection.
* A selected action is never an execution authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Generic, Hashable, Mapping, TypeVar

__all__ = [
    "EconomicCategory",
    "EconomicOpcode",
    "EconomicAction",
    "ExtendedEconomicAction",
    "EconomicFrame",
    "EconomicCodecError",
    "FondTransitionRelation",
    "FondPolicy",
    "category_for_byte",
    "encode_economic_frame",
    "decode_economic_frame",
    "hddl_action_symbol",
]


class EconomicCategory(str, Enum):
    NULL = "null"
    MARKET = "market"
    TRANSACTION = "transaction"
    PAYMENT_SETTLEMENT = "payment_settlement"
    LOGISTICS = "logistics"
    CONTRACT_RIGHTS = "contract_rights"
    PRODUCTION_SERVICE = "production_service"
    ACCOUNTING_FINANCE = "accounting_finance"
    GOVERNANCE_AUTHORITY = "governance_authority"
    EXTENSIONS = "extensions"
    ESCAPE = "escape"


class EconomicOpcode(IntEnum):
    UNKNOWN = 0x00

    QUOTE = 0x01
    OFFER = 0x02
    BID = 0x03
    ASK = 0x04
    DISCOVER = 0x05

    ORDER = 0x20
    FILL = 0x21
    SALE = 0x22
    PURCHASE = 0x23
    RETURN = 0x24
    CANCEL = 0x25
    EXCHANGE = 0x26

    INVOICE = 0x40
    PAY = 0x41
    SETTLE = 0x42
    REFUND = 0x43
    AUTHORIZE_PAYMENT = 0x44
    CAPTURE_PAYMENT = 0x45

    SHIP = 0x60
    DELIVER = 0x61
    RECEIVE = 0x62
    MOVE = 0x63
    STORE = 0x64
    CONSUME = 0x65

    SIGN = 0x80
    LICENSE = 0x81
    SUBSCRIBE = 0x82
    RENEW = 0x83
    TERMINATE = 0x84
    ASSIGN_RIGHT = 0x85

    MANUFACTURE = 0xA0
    DESIGN = 0xA1
    PRODUCE = 0xA2
    PROVIDE_SERVICE = 0xA3
    PROVE = 0xA4
    INSPECT = 0xA5
    ACCEPT = 0xA6

    ACCRUE = 0xC0
    RECOGNIZE_REVENUE = 0xC1
    RECOGNIZE_EXPENSE = 0xC2
    CAPITALIZE = 0xC3
    DEPRECIATE = 0xC4
    REALIZE_VALUE = 0xC5
    ALLOCATE = 0xC6

    OBSERVE = 0xE0
    AUTHORIZE = 0xE1
    ATTEST = 0xE2
    APPROVE = 0xE3
    REJECT = 0xE4
    DISPUTE = 0xE5
    RESOLVE = 0xE6

    EXTENDED = 0xFF

    @property
    def category(self) -> EconomicCategory:
        return category_for_byte(self.value)

    @property
    def canonical_name(self) -> str:
        return self.name.lower()


class EconomicCodecError(ValueError):
    """Typed planning-projection refusal for invalid economic frames."""


@dataclass(frozen=True)
class EconomicAction:
    """A grounded common-path economic action selected by a planner.

    ``parameters`` are immutable name/value pairs so the action remains hashable.
    They identify the grounded planning action; they are not execution authority.
    """

    opcode: EconomicOpcode
    parameters: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.opcode is EconomicOpcode.EXTENDED:
            raise EconomicCodecError(
                "0xFF requires ExtendedEconomicAction with a semantic identifier"
            )
        if len({name for name, _ in self.parameters}) != len(self.parameters):
            raise EconomicCodecError("economic action parameter names must be unique")

    @classmethod
    def grounded(cls, opcode: EconomicOpcode, **parameters: object) -> "EconomicAction":
        return cls(
            opcode=opcode,
            parameters=tuple(sorted((name, str(value)) for name, value in parameters.items())),
        )


@dataclass(frozen=True)
class ExtendedEconomicAction:
    """Lossless escape action for a semantic identifier outside the byte registry."""

    semantic_id: str
    parameters: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.semantic_id:
            raise EconomicCodecError("extended economic semantic identifier cannot be empty")
        if len({name for name, _ in self.parameters}) != len(self.parameters):
            raise EconomicCodecError("economic action parameter names must be unique")


EconomicFrame = EconomicAction | ExtendedEconomicAction


def category_for_byte(byte: int) -> EconomicCategory:
    if not 0 <= byte <= 0xFF:
        raise EconomicCodecError(f"economic opcode outside byte range: {byte!r}")
    if byte == 0x00:
        return EconomicCategory.NULL
    if byte <= 0x1F:
        return EconomicCategory.MARKET
    if byte <= 0x3F:
        return EconomicCategory.TRANSACTION
    if byte <= 0x5F:
        return EconomicCategory.PAYMENT_SETTLEMENT
    if byte <= 0x7F:
        return EconomicCategory.LOGISTICS
    if byte <= 0x9F:
        return EconomicCategory.CONTRACT_RIGHTS
    if byte <= 0xBF:
        return EconomicCategory.PRODUCTION_SERVICE
    if byte <= 0xDF:
        return EconomicCategory.ACCOUNTING_FINANCE
    if byte <= 0xEF:
        return EconomicCategory.GOVERNANCE_AUTHORITY
    if byte <= 0xFE:
        return EconomicCategory.EXTENSIONS
    return EconomicCategory.ESCAPE


def encode_economic_frame(frame: EconomicFrame) -> bytes:
    """Encode a planning action into the canonical wire identity.

    Grounded parameters are deliberately not serialized into this frame: the economic
    ABI is the verb identity, while parameters remain in the planning/domain state.
    """

    if isinstance(frame, ExtendedEconomicAction):
        payload = frame.semantic_id.encode("utf-8")
        if not payload:
            raise EconomicCodecError("extended economic semantic identifier cannot be empty")
        return bytes((EconomicOpcode.EXTENDED,)) + payload
    if frame.opcode is EconomicOpcode.EXTENDED:
        raise EconomicCodecError("0xFF requires an extended semantic identifier")
    return bytes((frame.opcode,))


def decode_economic_frame(data: bytes) -> EconomicFrame:
    """Decode exactly one canonical economic verb frame.

    Fixed actions must be exactly one byte. Unassigned bytes are refused rather than
    acquiring planner-local meanings. The 0xFF payload is retained losslessly as UTF-8.
    """

    if not data:
        raise EconomicCodecError("empty economic frame")

    head, payload = data[0], data[1:]
    if head == EconomicOpcode.EXTENDED:
        if not payload:
            raise EconomicCodecError("0xFF requires a semantic identifier")
        try:
            semantic_id = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EconomicCodecError("extended semantic identifier must be UTF-8") from exc
        return ExtendedEconomicAction(semantic_id=semantic_id)

    if payload:
        raise EconomicCodecError("fixed economic opcode must occupy exactly one byte")

    try:
        opcode = EconomicOpcode(head)
    except ValueError as exc:
        raise EconomicCodecError(f"unassigned economic opcode: 0x{head:02X}") from exc
    return EconomicAction(opcode=opcode)


def hddl_action_symbol(frame: EconomicFrame) -> str:
    """Return a stable HDDL/PDDL-safe primitive action symbol.

    Extended semantics deliberately share the symbol ``economic-extended``; the exact
    semantic identifier remains a separate grounded value rather than being lossy-normalized
    into a local action name.
    """

    if isinstance(frame, ExtendedEconomicAction):
        return "economic-extended"
    return "economic-" + frame.opcode.canonical_name.replace("_", "-")


S = TypeVar("S", bound=Hashable)


class FondTransitionRelation(Generic[S]):
    """Finite fully-observable nondeterministic successor relation.

    This represents only ``(state, selected_action) -> possible successor states``.
    It does not execute the selected economic action and carries no DO authority.
    """

    def __init__(
        self,
        transitions: Mapping[tuple[S, EconomicFrame], frozenset[S] | set[S]],
    ) -> None:
        normalized: dict[tuple[S, EconomicFrame], frozenset[S]] = {}
        for edge, successors in transitions.items():
            state, action = edge
            del state  # validates tuple unpacking without changing semantic identity
            frozen = frozenset(successors)
            if not frozen:
                raise EconomicCodecError(
                    f"FOND transition for {action!r} must admit at least one successor"
                )
            normalized[edge] = frozen
        self._transitions = MappingProxyType(normalized)

    def successors(self, state: S, action: EconomicFrame) -> frozenset[S]:
        try:
            return self._transitions[(state, action)]
        except KeyError as exc:
            raise EconomicCodecError(
                f"no admitted FOND transition for state={state!r}, action={action!r}"
            ) from exc

    def has_transition(self, state: S, action: EconomicFrame) -> bool:
        return (state, action) in self._transitions


class FondPolicy(Generic[S]):
    """Observation-to-action SELECT policy over a FOND relation.

    ``select`` yields a planning action only. The caller must separately cross its
    authority boundary before any external actuation.
    """

    def __init__(self, choices: Mapping[S, EconomicFrame]) -> None:
        self._choices = MappingProxyType(dict(choices))

    def select(self, state: S) -> EconomicFrame:
        try:
            action = self._choices[state]
        except KeyError as exc:
            raise EconomicCodecError(f"policy is undefined for state {state!r}") from exc
        if isinstance(action, EconomicAction) and action.opcode is EconomicOpcode.UNKNOWN:
            raise EconomicCodecError(
                "UNKNOWN is an observation boundary, not an executable policy action"
            )
        return action

    def successors(self, state: S, relation: FondTransitionRelation[S]) -> frozenset[S]:
        return relation.successors(state, self.select(state))
