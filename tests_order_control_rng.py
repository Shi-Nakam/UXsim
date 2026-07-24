# Verify World.order_control_rng initialization, reproducibility, and independence from W.rng.
#
# Run from the repository root:
#   python tests_order_control_rng.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import numpy as np

from uxsim import World


def _make_world(random_seed, name="order_control_rng_test"):
    return World(
        name=name,
        deltan=1,
        tmax=10,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=random_seed,
    )


def _draw_order_control_rng(W, count):
    return np.array([W.order_control_rng.random() for _ in range(count)])


def _draw_rng(W, count):
    return np.array([W.rng.random() for _ in range(count)])


def test_order_control_rng_exists_and_is_distinct_from_rng():
    W = _make_world(0)
    assert hasattr(W, "order_control_rng")
    assert W.order_control_rng is not W.rng


def test_order_control_rng_reproducible_for_same_random_seed():
    count = 5
    W1 = _make_world(0, name="order_control_rng_repro_1")
    W2 = _make_world(0, name="order_control_rng_repro_2")
    np.testing.assert_array_equal(
        _draw_order_control_rng(W1, count),
        _draw_order_control_rng(W2, count),
    )


def test_order_control_rng_differs_for_different_random_seed():
    count = 5
    W0 = _make_world(0, name="order_control_rng_seed_0")
    W1 = _make_world(1, name="order_control_rng_seed_1")
    samples_0 = _draw_order_control_rng(W0, count)
    samples_1 = _draw_order_control_rng(W1, count)
    assert not np.array_equal(samples_0, samples_1)


def test_order_control_rng_consumption_does_not_affect_rng():
    count = 5
    W_used = _make_world(0, name="order_control_rng_used")
    W_unused = _make_world(0, name="order_control_rng_unused")
    _draw_order_control_rng(W_used, count)
    np.testing.assert_array_equal(
        _draw_rng(W_used, count),
        _draw_rng(W_unused, count),
    )


def test_rng_sequence_unchanged_from_default_rng_initialization():
    count = 5
    W = _make_world(0, name="order_control_rng_main_rng")
    expected_rng = np.random.default_rng(seed=0)
    np.testing.assert_array_equal(
        _draw_rng(W, count),
        np.array([expected_rng.random() for _ in range(count)]),
    )


def test_random_seed_none_allows_both_generators():
    W = _make_world(None, name="order_control_rng_none_seed")
    assert W.rng.random() is not None
    assert W.order_control_rng.random() is not None


TESTS = [
    test_order_control_rng_exists_and_is_distinct_from_rng,
    test_order_control_rng_reproducible_for_same_random_seed,
    test_order_control_rng_differs_for_different_random_seed,
    test_order_control_rng_consumption_does_not_affect_rng,
    test_rng_sequence_unchanged_from_default_rng_initialization,
    test_random_seed_none_allows_both_generators,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control RNG tests passed.")
