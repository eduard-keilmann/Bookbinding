"""Translation contracts and structured errors used by the UI."""

from string import Formatter

import pytest

from bookbinding import make_plan
from bookbinding.errors import UserMessageError
from bookbinding.i18n import ENGLISH, Translator


def test_every_translation_preserves_format_fields():
    for german, english in ENGLISH.items():

        def fields(text):
            return sorted(field for _, field, _, _ in Formatter().parse(text) if field is not None)

        assert fields(german) == fields(english), german


def test_validation_error_can_be_rendered_in_both_languages():
    with pytest.raises(UserMessageError) as caught:
        make_plan(9, signature_sizes=[1])
    error = caught.value
    assert isinstance(error, ValueError)
    assert "zu klein" in str(error)
    english = Translator().text(error.message, **error.values)
    assert "too small: 4 spaces for 12 book pages" in english
    assert Translator("de").text(error.message, **error.values) == str(error)


def test_unknown_messages_and_languages_fail_explicitly():
    with pytest.raises(KeyError):
        Translator().text("missing message")
    with pytest.raises(ValueError):
        Translator("fr").text("Bereit")
