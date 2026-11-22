# Stored World entropy and the pure keyed uniform helper.
#
# This file does not exercise route choice, arrival tiebreakers, merge
# selection, or vehicle counters. Those connections are later units.
#
# Run from the repository root:
#   python tests_common_seed_rng_keyed_uniform.py

import ast
import pickle

import numpy as np

from uxsim import World
from uxsim.common_seed_rng_keyed_uniform import (
    FORMAT_PREFIX,
    SERIALIZATION_VERSION,
    _serialize_keyed_material,
    _sha256_digest,
    _uniform_value_from_digest,
    keyed_uniform_value,
    normalize_seed_sequence_entropy,
)


def _make_world(random_seed, name="common_seed_rng_keyed_uniform"):
    return World(
        name=name,
        deltan=1,
        tmax=10,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=random_seed,
    )


def _assert_entropy_tuple(entropy):
    assert type(entropy) is tuple
    assert len(entropy) >= 1
    for word in entropy:
        assert type(word) is int
        assert not isinstance(word, bool)
        assert word >= 0


def _assert_value_error(function, *args):
    try:
        function(*args)
    except ValueError:
        return
    raise AssertionError(f"{function.__name__} did not raise ValueError")


def _draw_rng(generator, count):
    draws = []
    index = 0
    while index < count:
        draws.append(generator.random())
        index += 1
    return draws


def test_same_explicit_seed_has_same_internal_entropy():
    first = _make_world(0, name="entropy_same_a")
    second = _make_world(0, name="entropy_same_b")
    _assert_entropy_tuple(first._common_seed_rng_internal_entropy)
    assert first._common_seed_rng_internal_entropy == (0,)
    assert (
        first._common_seed_rng_internal_entropy
        == second._common_seed_rng_internal_entropy
    )


def test_different_explicit_seed_has_different_internal_entropy():
    seed_zero = _make_world(0, name="entropy_seed_0")
    seed_one = _make_world(1, name="entropy_seed_1")
    assert seed_zero._common_seed_rng_internal_entropy == (0,)
    assert seed_one._common_seed_rng_internal_entropy == (1,)
    assert (
        seed_zero._common_seed_rng_internal_entropy
        != seed_one._common_seed_rng_internal_entropy
    )


def test_explicit_seed_seven_normalizes_to_tuple_of_seven():
    world = _make_world(7, name="entropy_seed_7")
    assert world._common_seed_rng_internal_entropy == (7,)


def test_random_seed_none_stores_a_valid_internal_entropy():
    world = _make_world(None, name="entropy_none")
    _assert_entropy_tuple(world._common_seed_rng_internal_entropy)
    assert world.random_seed is None


def test_none_world_copy_keeps_internal_entropy_on_a_different_object():
    world = _make_world(None, name="entropy_none_copy")
    copied = world.copy()
    assert copied is not world
    assert (
        copied._common_seed_rng_internal_entropy
        == world._common_seed_rng_internal_entropy
    )


def test_rewriting_public_random_seed_does_not_change_internal_entropy():
    world = _make_world(7, name="entropy_rewrite_public_seed")
    stored = world._common_seed_rng_internal_entropy
    world.random_seed = None
    assert world._common_seed_rng_internal_entropy == stored
    world.random_seed = 12345
    assert world._common_seed_rng_internal_entropy == stored
    assert world.random_seed == 12345


def test_internal_entropy_is_pickleable_python_ints():
    world = _make_world(4, name="entropy_pickle")
    restored = pickle.loads(pickle.dumps(world._common_seed_rng_internal_entropy))
    assert restored == world._common_seed_rng_internal_entropy
    assert type(restored) is tuple


def test_existing_rng_initial_sequence_matches_default_rng():
    world = _make_world(0, name="entropy_main_rng_sequence")
    expected = np.random.default_rng(seed=0)
    assert _draw_rng(world.rng, 5) == _draw_rng(expected, 5)


def test_existing_order_control_rng_sequence_matches_spawn_contract():
    world = _make_world(0, name="entropy_order_control_sequence")
    seed_sequence = np.random.SeedSequence(0)
    child_sequence = seed_sequence.spawn(1)[0]
    expected = np.random.default_rng(child_sequence)
    assert _draw_rng(world.order_control_rng, 5) == _draw_rng(expected, 5)


def test_keyed_helper_does_not_consume_world_rng_streams():
    used = _make_world(0, name="entropy_stream_used")
    idle = _make_world(0, name="entropy_stream_idle")
    keyed_uniform_value(
        used._common_seed_rng_internal_entropy,
        "test-domain",
        ("vehicle-a", 1),
    )
    assert _draw_rng(used.rng, 4) == _draw_rng(idle.rng, 4)
    assert _draw_rng(used.order_control_rng, 4) == _draw_rng(
        idle.order_control_rng,
        4,
    )


def test_same_key_is_stable_across_call_order():
    entropy = (9, 8, 7)
    domain = "test-domain"
    key_parts = ("vehicle-a", 3)
    first = keyed_uniform_value(entropy, domain, key_parts)
    keyed_uniform_value(entropy, domain, ("other-vehicle", 1))
    second = keyed_uniform_value(entropy, domain, key_parts)
    third = keyed_uniform_value(entropy, "other-domain", key_parts)
    again = keyed_uniform_value(entropy, domain, key_parts)
    assert first == second
    assert second == again
    assert first != third


def test_different_explicit_world_seeds_change_a_representative_key():
    seed_zero = _make_world(0, name="keyed_seed_0")
    seed_one = _make_world(1, name="keyed_seed_1")
    key_parts = ("representative", 0)
    value_zero = keyed_uniform_value(
        seed_zero._common_seed_rng_internal_entropy,
        "test-domain",
        key_parts,
    )
    value_one = keyed_uniform_value(
        seed_one._common_seed_rng_internal_entropy,
        "test-domain",
        key_parts,
    )
    assert value_zero != value_one


def test_domain_and_key_order_change_the_value():
    entropy = (1, 2)
    forward = keyed_uniform_value(entropy, "origin", ("link-a", "link-b"))
    swapped_parts = keyed_uniform_value(entropy, "origin", ("link-b", "link-a"))
    other_domain = keyed_uniform_value(entropy, "in-trip", ("link-a", "link-b"))
    assert forward != swapped_parts
    assert forward != other_domain


def test_string_and_integer_boundaries_do_not_collide():
    entropy = (3,)
    ab_c = _serialize_keyed_material(entropy, "boundary", ("ab", "c"))
    a_bc = _serialize_keyed_material(entropy, "boundary", ("a", "bc"))
    one_then_23 = _serialize_keyed_material(entropy, "boundary", (1, 23))
    twelve_then_3 = _serialize_keyed_material(entropy, "boundary", (12, 3))
    string_one = _serialize_keyed_material(entropy, "boundary", ("1",))
    integer_one = _serialize_keyed_material(entropy, "boundary", (1,))
    domain_a = _serialize_keyed_material(entropy, "domain-a", ("same",))
    domain_b = _serialize_keyed_material(entropy, "domain-b", ("same",))
    assert ab_c != a_bc
    assert one_then_23 != twelve_then_3
    assert string_one != integer_one
    assert domain_a != domain_b
    assert keyed_uniform_value(entropy, "boundary", ("ab", "c")) != (
        keyed_uniform_value(entropy, "boundary", ("a", "bc"))
    )
    assert keyed_uniform_value(entropy, "boundary", (1, 23)) != (
        keyed_uniform_value(entropy, "boundary", (12, 3))
    )
    assert keyed_uniform_value(entropy, "boundary", ("1",)) != (
        keyed_uniform_value(entropy, "boundary", (1,))
    )


def test_unicode_key_is_stable_and_distinct_from_ascii():
    entropy = (11,)
    unicode_key = ("交差点",)
    first = keyed_uniform_value(entropy, "test-domain", unicode_key)
    second = keyed_uniform_value(entropy, "test-domain", unicode_key)
    ascii_value = keyed_uniform_value(entropy, "test-domain", ("node",))
    assert first == second
    assert first != ascii_value
    unicode_bytes = _serialize_keyed_material(entropy, "test-domain", unicode_key)
    assert FORMAT_PREFIX in unicode_bytes


def test_uniform_value_is_inside_half_open_unit_interval():
    entropy = (0, 1, 2, 3)
    values = []
    part_index = 0
    while part_index < 20:
        values.append(
            keyed_uniform_value(entropy, "test-domain", ("vehicle", part_index))
        )
        part_index += 1
    for value in values:
        assert type(value) is float
        assert 0.0 <= value < 1.0


def test_world_copy_preserves_keyed_uniform_value():
    world = _make_world(6, name="keyed_copy")
    copied = world.copy()
    key_parts = ("copied-vehicle", 4)
    original_value = keyed_uniform_value(
        world._common_seed_rng_internal_entropy,
        "test-domain",
        key_parts,
    )
    copied_value = keyed_uniform_value(
        copied._common_seed_rng_internal_entropy,
        "test-domain",
        key_parts,
    )
    assert original_value == copied_value


def test_invalid_key_material_is_rejected():
    entropy = (1,)
    _assert_value_error(keyed_uniform_value, entropy, "test-domain", (True,))
    _assert_value_error(keyed_uniform_value, entropy, "test-domain", (False,))
    _assert_value_error(keyed_uniform_value, entropy, "test-domain", (-1,))
    _assert_value_error(keyed_uniform_value, entropy, "", ("vehicle",))
    _assert_value_error(keyed_uniform_value, entropy, "test-domain", ("",))
    _assert_value_error(keyed_uniform_value, entropy, "test-domain", (1.5,))
    _assert_value_error(keyed_uniform_value, entropy, "test-domain", ["vehicle"])
    _assert_value_error(keyed_uniform_value, (True,), "test-domain", ("vehicle",))
    _assert_value_error(keyed_uniform_value, (), "test-domain", ("vehicle",))
    _assert_value_error(keyed_uniform_value, entropy, "test-domain", ())


def test_normalize_seed_sequence_entropy_accepts_integers():
    assert normalize_seed_sequence_entropy(0) == (0,)
    assert normalize_seed_sequence_entropy(7) == (7,)
    numpy_seven = np.int64(7)
    assert normalize_seed_sequence_entropy(numpy_seven) == (7,)
    assert normalize_seed_sequence_entropy((1, 2)) == (1, 2)
    assert normalize_seed_sequence_entropy([1, 2]) == (1, 2)


def test_normalize_seed_sequence_entropy_rejects_invalid_input():
    _assert_value_error(normalize_seed_sequence_entropy, True)
    _assert_value_error(normalize_seed_sequence_entropy, False)
    _assert_value_error(normalize_seed_sequence_entropy, -1)
    _assert_value_error(normalize_seed_sequence_entropy, 1.5)
    _assert_value_error(normalize_seed_sequence_entropy, "1")
    _assert_value_error(normalize_seed_sequence_entropy, b"\x01")
    _assert_value_error(normalize_seed_sequence_entropy, bytearray(b"\x01"))
    _assert_value_error(normalize_seed_sequence_entropy, {1: "value"})
    _assert_value_error(normalize_seed_sequence_entropy, None)
    _assert_value_error(normalize_seed_sequence_entropy, ())
    _assert_value_error(normalize_seed_sequence_entropy, [])
    _assert_value_error(normalize_seed_sequence_entropy, (1.5,))
    _assert_value_error(normalize_seed_sequence_entropy, (1, True))


def test_serialization_prefix_records_the_version():
    serialized = _serialize_keyed_material((1, 2), "test-domain", ("vehicle", 0))
    assert serialized.startswith(FORMAT_PREFIX)
    expected_prefix = (
        b"UXSIM_COMMON_SEED_RNG_V" + str(SERIALIZATION_VERSION).encode("ascii")
    )
    assert FORMAT_PREFIX == expected_prefix
    assert FORMAT_PREFIX == b"UXSIM_COMMON_SEED_RNG_V1"


# Serialization version 1 fixed vector. entropy=(1,), domain="d", key=("a", 1).
# If FORMAT_PREFIX or the field layout changes on purpose, update these literals.
FIXED_VECTOR_SERIALIZATION_HEX = "555853494d5f434f4d4d4f4e5f534545445f524e475f5631450000000000000001000000000000000101440000000000000001640000000000000002530000000000000001614900000000000000000101"
FIXED_VECTOR_DIGEST_HEX = (
    "02b81eccf53766e351c8bc3b042a94a09aa4fcb972b99fcb205ab2793870e199"
)
FIXED_VECTOR_53_BIT_INTEGER = 95674047571692


def test_serialization_version_1_fixed_vector():
    internal_entropy = (1,)
    domain = "d"
    key_parts = ("a", 1)
    serialized = _serialize_keyed_material(internal_entropy, domain, key_parts)
    assert serialized.hex() == FIXED_VECTOR_SERIALIZATION_HEX
    digest = _sha256_digest(serialized)
    assert digest.hex() == FIXED_VECTOR_DIGEST_HEX
    expected_uniform = FIXED_VECTOR_53_BIT_INTEGER / (1 << 53)
    assert _uniform_value_from_digest(digest) == expected_uniform
    assert keyed_uniform_value(internal_entropy, domain, key_parts) == (
        expected_uniform
    )


def test_keyed_module_does_not_call_shared_rng_constructors():
    import uxsim.common_seed_rng_keyed_uniform as keyed_module

    with open(keyed_module.__file__, encoding="utf-8") as source_file:
        source_text = source_file.read()
    syntax_tree = ast.parse(source_text)
    forbidden_calls = []
    for node in ast.walk(syntax_tree):
        if type(node) is not ast.Call:
            continue
        called = node.func
        if type(called) is ast.Name and called.id in ("hash", "id"):
            forbidden_calls.append(called.id)
        if type(called) is ast.Attribute and called.attr in (
            "default_rng",
            "SeedSequence",
        ):
            forbidden_calls.append(called.attr)
        if (
            type(called) is ast.Attribute
            and called.attr == "random"
            and type(called.value) is ast.Name
            and called.value.id == "random"
        ):
            forbidden_calls.append("random.random")
    assert forbidden_calls == []


TESTS = [
    test_same_explicit_seed_has_same_internal_entropy,
    test_different_explicit_seed_has_different_internal_entropy,
    test_explicit_seed_seven_normalizes_to_tuple_of_seven,
    test_random_seed_none_stores_a_valid_internal_entropy,
    test_none_world_copy_keeps_internal_entropy_on_a_different_object,
    test_rewriting_public_random_seed_does_not_change_internal_entropy,
    test_internal_entropy_is_pickleable_python_ints,
    test_existing_rng_initial_sequence_matches_default_rng,
    test_existing_order_control_rng_sequence_matches_spawn_contract,
    test_keyed_helper_does_not_consume_world_rng_streams,
    test_same_key_is_stable_across_call_order,
    test_different_explicit_world_seeds_change_a_representative_key,
    test_domain_and_key_order_change_the_value,
    test_string_and_integer_boundaries_do_not_collide,
    test_unicode_key_is_stable_and_distinct_from_ascii,
    test_uniform_value_is_inside_half_open_unit_interval,
    test_world_copy_preserves_keyed_uniform_value,
    test_invalid_key_material_is_rejected,
    test_normalize_seed_sequence_entropy_accepts_integers,
    test_normalize_seed_sequence_entropy_rejects_invalid_input,
    test_serialization_prefix_records_the_version,
    test_serialization_version_1_fixed_vector,
    test_keyed_module_does_not_call_shared_rng_constructors,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Common seed/RNG keyed uniform tests passed.")
