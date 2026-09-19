# Unit tests for order-control DELTAN=1 validation (design notes 2, downstream boundary spec).
#
# Run from the repository root:
#   python tests_order_control_deltan.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

from pathlib import Path

from uxsim import World
from uxsim.uxsim import _validate_order_control_deltan

_UXSIM_SOURCE_PATH = Path(__file__).resolve().parent / "uxsim" / "uxsim.py"

_INVALID_DELTAN_VALUES = (
    True,
    False,
    0,
    2,
    5,
    1.0,
    "1",
    None,
)

_ORDER_CONTROL_TYPES_NON_NONE = ("fcfs", "batch", "time_value")

_ERROR_SUBSTRINGS = (
    "DELTAN=1",
    "FCFS",
    "BATCH",
    "TVT",
    "Vehicle",
)


def _expect_value_error(callable_obj, *, message_substrings=()):
    try:
        callable_obj()
    except ValueError as error:
        message = str(error)
        for substring in message_substrings:
            assert substring in message, (
                f"expected {substring!r} in error message; got {message!r}"
            )
        return message
    raise AssertionError("expected ValueError")


def _build_world(*, deltan=1, name="order_control_deltan"):
    return World(
        name=name,
        deltan=deltan,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )


def _build_merge_network(W):
    W.addNode("orig1", 0, 1)
    W.addNode("orig2", 0, -1)
    merge = W.addNode("merge", 1, 0)
    W.addNode("dest", 2, 0)
    W.addLink(
        "link1",
        "orig1",
        "merge",
        length=500,
        free_flow_speed=16.67,
        number_of_lanes=1,
    )
    W.addLink(
        "link2",
        "orig2",
        "merge",
        length=500,
        free_flow_speed=16.67,
        number_of_lanes=1,
    )
    W.addLink(
        "link3",
        "merge",
        "dest",
        length=500,
        free_flow_speed=16.67,
        number_of_lanes=1,
    )
    W.infer_order_control_eligible_nodes()
    assert merge.order_control_eligible is True
    return merge


def _snapshot_node_settings(node):
    return {
        "order_control_type": node.order_control_type,
        "batch_size": node.batch_size,
        "transaction_case": node.transaction_case,
        "order_control_batch_t_trigger_level": node.order_control_batch_t_trigger_level,
        "order_control_batch_virtual_horizon": node.order_control_batch_virtual_horizon,
    }


def test_validate_order_control_deltan_accepts_one():
    _validate_order_control_deltan(1)


def test_validate_order_control_deltan_rejects_invalid_values():
    for invalid_value in _INVALID_DELTAN_VALUES:
        message = _expect_value_error(
            lambda value=invalid_value: _validate_order_control_deltan(value),
            message_substrings=_ERROR_SUBSTRINGS,
        )
        assert repr(invalid_value) in message or str(invalid_value) in message
        assert type(invalid_value).__name__ in message
        assert "type<class" not in message


def test_validate_order_control_deltan_rejects_true_with_type_in_message():
    message = _expect_value_error(
        lambda: _validate_order_control_deltan(True),
        message_substrings=_ERROR_SUBSTRINGS,
    )
    assert "got DELTAN=True with type bool." in message
    assert "type<class" not in message


def test_validate_order_control_deltan_error_uses_readable_type_names():
    expected_fragments = (
        (True, "got DELTAN=True with type bool."),
        (1.0, "got DELTAN=1.0 with type float."),
        ("1", "got DELTAN='1' with type str."),
        (None, "got DELTAN=None with type NoneType."),
    )
    for invalid_value, expected_fragment in expected_fragments:
        message = _expect_value_error(
            lambda value=invalid_value: _validate_order_control_deltan(value),
            message_substrings=_ERROR_SUBSTRINGS,
        )
        assert expected_fragment in message
        assert "type<class" not in message


def test_addnode_non_none_order_control_succeeds_when_deltan_is_one():
    W = _build_world(name="addnode_deltan_ok")
    for order_control_type in _ORDER_CONTROL_TYPES_NON_NONE:
        node_name = f"node_{order_control_type}"
        kwargs = {
            "order_control_eligible": True,
            "order_control_type": order_control_type,
        }
        if order_control_type == "time_value":
            kwargs["transaction_case"] = "I"
        if order_control_type == "batch":
            kwargs["batch_size"] = 3
        node = W.addNode(node_name, 0, 0, **kwargs)
        assert node.order_control_type == order_control_type


def test_addnode_non_none_order_control_rejects_invalid_deltan():
    for order_control_type in _ORDER_CONTROL_TYPES_NON_NONE:
        W = _build_world(
            name=f"addnode_bad_deltan_{order_control_type}",
            deltan=2,
        )
        node_count_before = len(W.NODES)
        node_name = f"bad_{order_control_type}"
        kwargs = {
            "order_control_eligible": True,
            "order_control_type": order_control_type,
        }
        if order_control_type == "time_value":
            kwargs["transaction_case"] = "I"

        _expect_value_error(
            lambda: W.addNode(node_name, 0, 0, **kwargs),
            message_substrings=_ERROR_SUBSTRINGS,
        )
        assert len(W.NODES) == node_count_before
        assert node_name not in W.NODES_NAME_DICT


def test_addnode_none_order_control_allowed_when_deltan_is_not_one():
    W = _build_world(name="addnode_none_bad_deltan", deltan=5)
    node = W.addNode("plain", 0, 0, order_control_type="none")
    assert node.order_control_type == "none"


def test_addnode_failure_does_not_break_existing_nodes():
    W = _build_world(name="addnode_existing_preserved", deltan=2)
    existing = W.addNode("existing", 0, 0)
    before = len(W.NODES)
    _expect_value_error(
        lambda: W.addNode(
            "new_fcfs",
            1,
            0,
            order_control_eligible=True,
            order_control_type="fcfs",
        ),
        message_substrings=_ERROR_SUBSTRINGS,
    )
    assert len(W.NODES) == before
    assert existing in W.NODES
    assert existing.order_control_type == "none"


def test_set_order_control_for_nodes_succeeds_when_deltan_is_one():
    W = _build_world(name="setter_deltan_ok")
    merge = _build_merge_network(W)
    for order_control_type in _ORDER_CONTROL_TYPES_NON_NONE:
        kwargs = {"order_control_type": order_control_type}
        if order_control_type == "time_value":
            kwargs["transaction_case"] = "I"
        if order_control_type == "batch":
            kwargs["batch_size"] = 4
            kwargs["order_control_batch_virtual_horizon"] = 40
        configured = W.set_order_control_for_nodes([merge.name], **kwargs)
        assert configured[0].order_control_type == order_control_type
        merge.order_control_type = "none"
        merge.batch_size = 1
        merge.transaction_case = None
        merge.order_control_batch_t_trigger_level = 1
        merge.order_control_batch_virtual_horizon = 30


def test_set_order_control_for_nodes_rejects_invalid_deltan_for_non_none():
    for order_control_type in _ORDER_CONTROL_TYPES_NON_NONE:
        W = _build_world(
            name=f"setter_bad_deltan_{order_control_type}",
            deltan=2,
        )
        merge = _build_merge_network(W)
        before = _snapshot_node_settings(merge)
        kwargs = {"order_control_type": order_control_type}
        if order_control_type == "time_value":
            kwargs["transaction_case"] = "I"
        if order_control_type == "batch":
            kwargs["batch_size"] = 7
            kwargs["order_control_batch_t_trigger_level"] = 2
            kwargs["order_control_batch_virtual_horizon"] = 55

        _expect_value_error(
            lambda: W.set_order_control_for_nodes([merge.name], **kwargs),
            message_substrings=_ERROR_SUBSTRINGS,
        )
        assert _snapshot_node_settings(merge) == before


def test_set_order_control_for_nodes_atomic_for_multiple_nodes():
    W = _build_world(name="setter_multi_atomic", deltan=3)
    merge_a = _build_merge_network(W)
    W.addNode("orig3", 0, 2)
    merge_b = W.addNode("merge2", 1, 2)
    W.addNode("orig4", 0, 3)
    W.addNode("dest2", 2, 2)
    W.addLink("link4a", "orig3", "merge2", length=500, free_flow_speed=16.67, number_of_lanes=1)
    W.addLink("link4b", "orig4", "merge2", length=500, free_flow_speed=16.67, number_of_lanes=1)
    W.addLink("link4c", "merge2", "dest2", length=500, free_flow_speed=16.67, number_of_lanes=1)
    W.infer_order_control_eligible_nodes()
    assert merge_b.order_control_eligible is True

    before_a = _snapshot_node_settings(merge_a)
    before_b = _snapshot_node_settings(merge_b)

    _expect_value_error(
        lambda: W.set_order_control_for_nodes(
            [merge_a.name, merge_b.name],
            order_control_type="fcfs",
        ),
        message_substrings=_ERROR_SUBSTRINGS,
    )
    assert _snapshot_node_settings(merge_a) == before_a
    assert _snapshot_node_settings(merge_b) == before_b


def test_set_order_control_for_nodes_none_allowed_when_deltan_is_not_one():
    W = _build_world(name="setter_none_bad_deltan", deltan=5)
    merge = _build_merge_network(W)
    merge.order_control_type = "fcfs"
    configured = W.set_order_control_for_nodes([merge.name], order_control_type="none")
    assert configured[0].order_control_type == "none"


def test_random_selection_succeeds_when_deltan_is_one():
    W = _build_world(name="random_deltan_ok")
    _build_merge_network(W)
    W.addNode("orig5", 0, 4)
    W.addNode("orig6", 0, 5)
    merge2 = W.addNode("merge3", 1, 4)
    W.addNode("dest3", 2, 4)
    W.addLink("link5a", "orig5", "merge3", length=500, free_flow_speed=16.67, number_of_lanes=1)
    W.addLink("link5b", "orig6", "merge3", length=500, free_flow_speed=16.67, number_of_lanes=1)
    W.addLink("link5c", "merge3", "dest3", length=500, free_flow_speed=16.67, number_of_lanes=1)
    W.infer_order_control_eligible_nodes()
    assert merge2.order_control_eligible is True

    selected = W.set_order_control_for_randomly_selected_eligible_nodes(
        fraction=0.5,
        order_control_type="batch",
        batch_size=10,
        random_seed=0,
    )
    assert len(selected) >= 1
    for node in selected:
        assert node.order_control_type == "batch"


def test_random_selection_rejects_invalid_deltan_via_setter():
    W = _build_world(name="random_deltan_bad", deltan=2)
    merge = _build_merge_network(W)
    before = _snapshot_node_settings(merge)
    _expect_value_error(
        lambda: W.set_order_control_for_randomly_selected_eligible_nodes(
            fraction=1.0,
            order_control_type="fcfs",
            random_seed=0,
        ),
        message_substrings=_ERROR_SUBSTRINGS,
    )
    assert _snapshot_node_settings(merge) == before


def test_random_selection_fraction_zero_does_not_invoke_deltan_validator():
    W = _build_world(name="random_fraction_zero", deltan=5)
    _build_merge_network(W)
    assert W.set_order_control_for_randomly_selected_eligible_nodes(
        fraction=0,
        order_control_type="fcfs",
        random_seed=0,
    ) == []


def test_random_path_does_not_duplicate_deltan_validator_in_source():
    source_text = _UXSIM_SOURCE_PATH.read_text(encoding="utf-8")
    random_function_start = source_text.index(
        "def set_order_control_for_randomly_selected_eligible_nodes("
    )
    random_function_end = source_text.index(
        "def addLink(W, name: str, start_node: Node|str, end_node: Node|str, length: float",
        random_function_start,
    )
    random_function_source = source_text[random_function_start:random_function_end]
    assert "_validate_order_control_deltan" not in random_function_source


def test_deltan_validator_not_called_from_simulation_or_transfer_paths():
    source_text = _UXSIM_SOURCE_PATH.read_text(encoding="utf-8")
    forbidden_contexts = (
        "def transfer(",
        "def exec_simulation(",
        "def update(s):",
    )
    for marker in forbidden_contexts:
        marker_index = source_text.find(marker)
        if marker_index == -1:
            continue
        next_def_index = source_text.find("\n    def ", marker_index + 1)
        if next_def_index == -1:
            next_def_index = len(source_text)
        block = source_text[marker_index:next_def_index]
        assert "_validate_order_control_deltan" not in block


TESTS = [
    test_validate_order_control_deltan_accepts_one,
    test_validate_order_control_deltan_rejects_invalid_values,
    test_validate_order_control_deltan_rejects_true_with_type_in_message,
    test_validate_order_control_deltan_error_uses_readable_type_names,
    test_addnode_non_none_order_control_succeeds_when_deltan_is_one,
    test_addnode_non_none_order_control_rejects_invalid_deltan,
    test_addnode_none_order_control_allowed_when_deltan_is_not_one,
    test_addnode_failure_does_not_break_existing_nodes,
    test_set_order_control_for_nodes_succeeds_when_deltan_is_one,
    test_set_order_control_for_nodes_rejects_invalid_deltan_for_non_none,
    test_set_order_control_for_nodes_atomic_for_multiple_nodes,
    test_set_order_control_for_nodes_none_allowed_when_deltan_is_not_one,
    test_random_selection_succeeds_when_deltan_is_one,
    test_random_selection_rejects_invalid_deltan_via_setter,
    test_random_selection_fraction_zero_does_not_invoke_deltan_validator,
    test_random_path_does_not_duplicate_deltan_validator_in_source,
    test_deltan_validator_not_called_from_simulation_or_transfer_paths,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print(f"Order-control DELTAN validation tests passed ({len(TESTS)} tests).")
