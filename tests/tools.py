from typing import Any


def assert_calls_in_any_order(actual_calls: list[Any], expected_calls: list[Any]) -> None:
    expected_calls_copy = expected_calls.copy()
    for call_args in actual_calls:
        if call_args not in expected_calls_copy:
            raise AssertionError(f"Call {call_args} not found in expected calls")
        expected_calls_copy.remove(call_args)
