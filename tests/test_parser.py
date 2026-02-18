from app.horo.parser import sanitize_for_telegram_html, truncate_text


def test_sanitize_for_telegram_html_escapes_markup() -> None:
    source = '<a href="https://example.com">link</a> & text'
    result = sanitize_for_telegram_html(source)

    assert result == '&lt;a href="https://example.com"&gt;link&lt;/a&gt; &amp; text'


def test_truncate_text_short_string_unchanged() -> None:
    source = "short text"
    assert truncate_text(source, max_length=100) == source


def test_truncate_text_long_string_appends_ellipsis() -> None:
    source = "word " * 200
    result = truncate_text(source, max_length=120)

    assert len(result) <= 123
    assert result.endswith("...")
