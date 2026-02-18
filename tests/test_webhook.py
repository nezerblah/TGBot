from app.webhook import _extract_update_timestamp


def test_extract_update_timestamp_from_message() -> None:
    update = {"message": {"date": 1234567890}}
    assert _extract_update_timestamp(update) == 1234567890


def test_extract_update_timestamp_from_callback_message() -> None:
    update = {"callback_query": {"message": {"date": 1234567999}}}
    assert _extract_update_timestamp(update) == 1234567999


def test_extract_update_timestamp_when_absent() -> None:
    update = {"update_id": 1}
    assert _extract_update_timestamp(update) == 0
