import pytest

from skdecide.economic import (
    EconomicAction,
    EconomicCategory,
    EconomicCodecError,
    EconomicOpcode,
    ExtendedEconomicAction,
    FondPolicy,
    FondTransitionRelation,
    category_for_byte,
    decode_economic_frame,
    encode_economic_frame,
    hddl_action_symbol,
)


ASSIGNED = [opcode for opcode in EconomicOpcode if opcode is not EconomicOpcode.EXTENDED]


def test_assigned_common_path_opcodes_round_trip_as_single_bytes():
    seen = set()
    for opcode in ASSIGNED:
        frame = EconomicAction(opcode)
        encoded = encode_economic_frame(frame)
        assert len(encoded) == 1
        assert encoded[0] == opcode.value
        assert decode_economic_frame(encoded) == frame
        assert opcode.value not in seen
        seen.add(opcode.value)


def test_reserved_bytes_are_refused_not_reinterpreted():
    for byte in (0x06, 0x1F, 0x27, 0x3F, 0x46, 0x5F, 0x66, 0x7F, 0x86, 0x9F, 0xA7, 0xBF, 0xC7, 0xDF, 0xE7, 0xEF, 0xF0, 0xFE):
        with pytest.raises(EconomicCodecError, match="unassigned"):
            decode_economic_frame(bytes((byte,)))


def test_unknown_and_escape_boundaries_are_stable():
    assert EconomicOpcode.UNKNOWN.value == 0x00
    assert category_for_byte(0x00) is EconomicCategory.NULL
    assert EconomicOpcode.EXTENDED.value == 0xFF
    assert category_for_byte(0xFF) is EconomicCategory.ESCAPE


def test_extended_semantic_identifier_round_trips_losslessly():
    frame = ExtendedEconomicAction("urn:example:economic:custom-action")
    encoded = encode_economic_frame(frame)
    assert encoded[0] == 0xFF
    assert decode_economic_frame(encoded) == frame


def test_fixed_frame_rejects_trailing_payload():
    with pytest.raises(EconomicCodecError, match="exactly one byte"):
        decode_economic_frame(b"\x41\x00")


def test_hddl_symbols_are_stable_and_do_not_hide_extended_identity():
    assert hddl_action_symbol(EconomicAction(EconomicOpcode.PAY)) == "economic-pay"
    assert (
        hddl_action_symbol(EconomicAction(EconomicOpcode.RECOGNIZE_REVENUE))
        == "economic-recognize-revenue"
    )
    assert hddl_action_symbol(ExtendedEconomicAction("urn:x")) == "economic-extended"


def test_fond_relation_preserves_nondeterministic_successors():
    pay = EconomicAction.grounded(
        EconomicOpcode.PAY, payer="customer-1", payee="merchant-1", invoice="inv-1"
    )
    relation = FondTransitionRelation(
        {
            ("payment-pending", pay): {
                "settled",
                "declined",
                "disputed",
                "unknown",
            }
        }
    )
    assert relation.successors("payment-pending", pay) == frozenset(
        {"settled", "declined", "disputed", "unknown"}
    )


def test_fond_policy_is_select_only_and_unknown_cannot_be_executed():
    pay = EconomicAction(EconomicOpcode.PAY)
    policy = FondPolicy({"ready": pay})
    assert policy.select("ready") == pay

    unknown_policy = FondPolicy({"unresolved": EconomicAction(EconomicOpcode.UNKNOWN)})
    with pytest.raises(EconomicCodecError, match="observation boundary"):
        unknown_policy.select("unresolved")


def test_fond_policy_requires_explicitly_admitted_transition():
    pay = EconomicAction(EconomicOpcode.PAY)
    relation = FondTransitionRelation({("ready", pay): {"settled", "declined"}})
    policy = FondPolicy({"ready": pay, "other": pay})

    assert policy.successors("ready", relation) == frozenset({"settled", "declined"})
    with pytest.raises(EconomicCodecError, match="no admitted FOND transition"):
        policy.successors("other", relation)
