import sys
from unittest import mock

import pytest
from markupsafe import Markup
from ordered_set import OrderedSet

from emergency_alerts_utils.template import (
    BaseBroadcastTemplate,
    BroadcastMessageTemplate,
    BroadcastPreviewTemplate,
    SMSMessageTemplate,
    SMSPreviewTemplate,
    Template,
)


@pytest.mark.parametrize(
    "template_class, expected_error",
    (
        pytest.param(
            Template,
            ("Can't instantiate abstract class Template with abstract methods __str__"),
            marks=pytest.mark.skipif(sys.version_info >= (3, 9), reason="‘methods’ will be singular"),
        ),
        pytest.param(
            Template,
            ("Can't instantiate abstract class Template with abstract method __str__"),
            marks=pytest.mark.skipif(sys.version_info < (3, 9), reason="‘method’ will be pluralised"),
        ),
        pytest.param(
            BaseBroadcastTemplate,
            ("Can't instantiate abstract class BaseBroadcastTemplate with abstract methods __str__"),
            marks=pytest.mark.skipif(sys.version_info >= (3, 9), reason="‘methods’ will be singular"),
        ),
        pytest.param(
            BaseBroadcastTemplate,
            ("Can't instantiate abstract class BaseBroadcastTemplate with abstract method __str__"),
            marks=pytest.mark.skipif(sys.version_info < (3, 9), reason="‘method’ will be pluralised"),
        ),
    ),
)
def test_abstract_classes_cant_be_instantiated(template_class, expected_error):
    with pytest.raises(TypeError) as error:
        template_class({})
    assert str(error.value) == expected_error


@pytest.mark.parametrize(
    "template_class, expected_error",
    ((BroadcastPreviewTemplate, ("Cannot initialise BroadcastPreviewTemplate with sms template_type")),),
)
def test_errors_for_incompatible_template_type(template_class, expected_error):
    with pytest.raises(TypeError) as error:
        template_class({"content": "", "subject": "", "template_type": "sms"})
    assert str(error.value) == expected_error


@pytest.mark.parametrize(
    "template_class, template_type, extra_attributes",
    [
        (SMSPreviewTemplate, "sms", 'class="govuk-link govuk-link--no-visited-state"'),
        (BroadcastPreviewTemplate, "broadcast", 'class="govuk-link govuk-link--no-visited-state"'),
    ],
)
@pytest.mark.parametrize(
    "url, url_with_entities_replaced",
    [
        ("http://example.com", "http://example.com"),
        ("http://www.gov.uk/", "http://www.gov.uk/"),
        ("https://www.gov.uk/", "https://www.gov.uk/"),
        ("http://service.gov.uk", "http://service.gov.uk"),
        (
            "http://service.gov.uk/blah.ext?q=a%20b%20c&order=desc#fragment",
            "http://service.gov.uk/blah.ext?q=a%20b%20c&amp;order=desc#fragment",
        ),
        pytest.param("example.com", "example.com", marks=pytest.mark.xfail),
        pytest.param("www.example.com", "www.example.com", marks=pytest.mark.xfail),
        pytest.param(
            "http://service.gov.uk/blah.ext?q=one two three",
            "http://service.gov.uk/blah.ext?q=one two three",
            marks=pytest.mark.xfail,
        ),
        pytest.param("ftp://example.com", "ftp://example.com", marks=pytest.mark.xfail),
        pytest.param("mailto:test@example.com", "mailto:test@example.com", marks=pytest.mark.xfail),
    ],
)
def test_makes_links_out_of_URLs(extra_attributes, template_class, template_type, url, url_with_entities_replaced):
    assert f'<a {extra_attributes} href="{url_with_entities_replaced}">{url_with_entities_replaced}</a>' in str(
        template_class({"content": url, "subject": "", "template_type": template_type})
    )


@pytest.mark.parametrize(
    "template_class, template_type",
    (
        (SMSPreviewTemplate, "sms"),
        (BroadcastPreviewTemplate, "broadcast"),
    ),
)
@pytest.mark.parametrize(
    "url, url_with_entities_replaced",
    (
        ("example.com", "example.com"),
        ("www.gov.uk/", "www.gov.uk/"),
        ("service.gov.uk", "service.gov.uk"),
        ("gov.uk/coronavirus", "gov.uk/coronavirus"),
        (
            "service.gov.uk/blah.ext?q=a%20b%20c&order=desc#fragment",
            "service.gov.uk/blah.ext?q=a%20b%20c&amp;order=desc#fragment",
        ),
    ),
)
def test_makes_links_out_of_URLs_without_protocol_in_sms_and_broadcast(
    template_class,
    template_type,
    url,
    url_with_entities_replaced,
):
    assert (
        f"<a "
        f'class="govuk-link govuk-link--no-visited-state" '
        f'href="http://{url_with_entities_replaced}">'
        f"{url_with_entities_replaced}"
        f"</a>"
    ) in str(template_class({"content": url, "subject": "", "template_type": template_type}))


@mock.patch("emergency_alerts_utils.template.add_prefix", return_value="")
@pytest.mark.parametrize(
    "template_class, prefix, body, expected_call",
    [
        (SMSMessageTemplate, "a", "b", (Markup("b"), "a")),
        (SMSPreviewTemplate, "a", "b", (Markup("b"), "a")),
        (BroadcastPreviewTemplate, "a", "b", (Markup("b"), "a")),
        (SMSMessageTemplate, None, "b", (Markup("b"), None)),
        (SMSPreviewTemplate, None, "b", (Markup("b"), None)),
        (BroadcastPreviewTemplate, None, "b", (Markup("b"), None)),
        (SMSMessageTemplate, "<em>ht&ml</em>", "b", (Markup("b"), "<em>ht&ml</em>")),
        (SMSPreviewTemplate, "<em>ht&ml</em>", "b", (Markup("b"), "&lt;em&gt;ht&amp;ml&lt;/em&gt;")),
        (BroadcastPreviewTemplate, "<em>ht&ml</em>", "b", (Markup("b"), "&lt;em&gt;ht&amp;ml&lt;/em&gt;")),
    ],
)
def test_sms_message_adds_prefix(add_prefix, template_class, prefix, body, expected_call):
    template = template_class({"content": body, "template_type": template_class.template_type})
    template.prefix = prefix
    template.sender = None
    str(template)
    add_prefix.assert_called_once_with(*expected_call)


@mock.patch("emergency_alerts_utils.template.add_prefix", return_value="")
@pytest.mark.parametrize(
    "template_class",
    [
        SMSMessageTemplate,
        SMSPreviewTemplate,
        BroadcastPreviewTemplate,
    ],
)
@pytest.mark.parametrize(
    "show_prefix, prefix, body, sender, expected_call",
    [
        (False, "a", "b", "c", (Markup("b"), None)),
        (True, "a", "b", None, (Markup("b"), "a")),
        (True, "a", "b", False, (Markup("b"), "a")),
    ],
)
def test_sms_message_adds_prefix_only_if_asked_to(
    add_prefix,
    show_prefix,
    prefix,
    body,
    sender,
    expected_call,
    template_class,
):
    template = template_class(
        {"content": body, "template_type": template_class.template_type},
        prefix=prefix,
        show_prefix=show_prefix,
        sender=sender,
    )
    str(template)
    add_prefix.assert_called_once_with(*expected_call)


@pytest.mark.parametrize("content_to_look_for", ["GOVUK", "sms-message-sender"])
@pytest.mark.parametrize(
    "show_sender",
    [
        True,
        pytest.param(False, marks=pytest.mark.xfail),
    ],
)
def test_sms_message_preview_shows_sender(
    show_sender,
    content_to_look_for,
):
    assert content_to_look_for in str(
        SMSPreviewTemplate(
            {"content": "foo", "template_type": "sms"},
            sender="GOVUK",
            show_sender=show_sender,
        )
    )


def test_sms_message_preview_hides_sender_by_default():
    assert SMSPreviewTemplate({"content": "foo", "template_type": "sms"}).show_sender is False


@mock.patch("emergency_alerts_utils.template.sms_encode", return_value="downgraded")
@pytest.mark.parametrize(
    "template_class, extra_args, expected_call",
    (
        (SMSMessageTemplate, {"prefix": "Service name"}, "Service name: Message"),
        (SMSPreviewTemplate, {"prefix": "Service name"}, "Service name: Message"),
        (BroadcastMessageTemplate, {}, "Message"),
        (BroadcastPreviewTemplate, {"prefix": "Service name"}, "Service name: Message"),
    ),
)
def test_sms_messages_downgrade_non_sms(
    mock_sms_encode,
    template_class,
    extra_args,
    expected_call,
):
    template = str(template_class({"content": "Message", "template_type": template_class.template_type}, **extra_args))
    assert "downgraded" in str(template)
    mock_sms_encode.assert_called_once_with(expected_call)


@pytest.mark.parametrize(
    "template_class",
    (
        SMSPreviewTemplate,
        BroadcastPreviewTemplate,
    ),
)
@mock.patch("emergency_alerts_utils.template.sms_encode", return_value="downgraded")
def test_sms_messages_dont_downgrade_non_sms_if_setting_is_false(mock_sms_encode, template_class):
    template = str(
        template_class(
            {"content": "😎", "template_type": template_class.template_type},
            prefix="👉",
            downgrade_non_sms_characters=False,
        )
    )
    assert "👉: 😎" in str(template)
    assert mock_sms_encode.called is False


@pytest.mark.parametrize(
    "template_class",
    (
        SMSPreviewTemplate,
        BroadcastPreviewTemplate,
    ),
)
@mock.patch("emergency_alerts_utils.template.nl2br")
def test_sms_preview_adds_newlines(nl2br, template_class):
    content = "the\nquick\n\nbrown fox"
    str(template_class({"content": content, "template_type": template_class.template_type}))
    nl2br.assert_called_once_with(content)


@pytest.mark.parametrize(
    "content",
    [
        ("one newline\n" "two newlines\n" "\n" "end"),  # Unix-style
        ("one newline\r\n" "two newlines\r\n" "\r\n" "end"),  # Windows-style
        ("one newline\r" "two newlines\r" "\r" "end"),  # Mac Classic style
        ("\t\t\n\r one newline\n" "two newlines\r" "\r\n" "end\n\n  \r \n \t "),  # A mess
    ],
)
def test_sms_message_normalises_newlines(content):
    assert repr(str(SMSMessageTemplate({"content": content, "template_type": "sms"}))) == repr(
        "one newline\n" "two newlines\n" "\n" "end"
    )


@pytest.mark.parametrize(
    "content",
    [
        ("one newline\n" "two newlines\n" "\n" "end"),  # Unix-style
        ("one newline\r\n" "two newlines\r\n" "\r\n" "end"),  # Windows-style
        ("one newline\r" "two newlines\r" "\r" "end"),  # Mac Classic style
        ("\t\t\n\r one newline\xa0\n" "two newlines\r" "\r\n" "end\n\n  \r \n \t "),  # A mess
    ],
)
def test_broadcast_message_normalises_newlines(content):
    assert str(BroadcastMessageTemplate({"content": content, "template_type": "broadcast"})) == (
        "one newline\n" "two newlines\n" "\n" "end"
    )


@pytest.mark.parametrize(
    "template_class",
    (
        SMSMessageTemplate,
        BroadcastMessageTemplate,
        # Note: BroadcastPreviewTemplate not tested here
        # as this will render full HTML template, not just the body
    ),
)
def test_phone_templates_normalise_whitespace(template_class):
    content = "  Hi\u00A0there\u00A0 what's\u200D up\t"
    assert (
        str(template_class({"content": content, "template_type": template_class.template_type})) == "Hi there what's up"
    )


@pytest.mark.parametrize(
    "template_class",
    (
        SMSMessageTemplate,
        SMSPreviewTemplate,
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ),
)
@pytest.mark.parametrize(
    "template_json",
    (
        {"content": ""},
        {"content": "", "subject": "subject"},
    ),
)
def test_sms_templates_have_no_subject(template_class, template_json):
    template_json.update(template_type=template_class.template_type)
    assert not hasattr(
        template_class(template_json),
        "subject",
    )


@pytest.mark.parametrize(
    "template_class",
    [
        SMSMessageTemplate,
        SMSPreviewTemplate,
    ],
)
@pytest.mark.parametrize(
    "content, values, prefix, expected_count_in_template, expected_count_in_notification",
    [
        # is an unsupported unicode character so should be replaced with a ?
        ("深", {}, None, 1, 1),
        # is a supported unicode character so should be kept as is
        ("Ŵ", {}, None, 1, 1),
        ("'First line.\n", {}, None, 12, 12),
        ("\t\n\r", {}, None, 0, 0),
        ("Content with ((placeholder))", {"placeholder": "something extra here"}, None, 13, 33),
        ("Content with ((placeholder))", {"placeholder": ""}, None, 13, 12),
        ("Just content", {}, None, 12, 12),
        ("((placeholder))  ", {"placeholder": "  "}, None, 0, 0),
        ("  ", {}, None, 0, 0),
        ("Content with ((placeholder))", {"placeholder": "something extra here"}, "GDS", 18, 38),
        ("Just content", {}, "GDS", 17, 17),
        ("((placeholder))  ", {"placeholder": "  "}, "GDS", 5, 4),
        ("  ", {}, "GDS", 4, 4),  # Becomes `GDS:`
        ("  G      D       S  ", {}, None, 5, 5),  # Becomes `G D S`
        ("P1 \n\n\n\n\n\n P2", {}, None, 6, 6),  # Becomes `P1\n\nP2`
        ("a    ((placeholder))    b", {"placeholder": ""}, None, 4, 3),  # Counted as `a  b` then `a b`
    ],
)
def test_character_count_for_sms_templates(
    content, values, prefix, expected_count_in_template, expected_count_in_notification, template_class
):
    template = template_class(
        {"content": content, "template_type": "sms"},
        prefix=prefix,
    )
    template.sender = None
    assert template.content_count == expected_count_in_template
    template.values = values
    assert template.content_count == expected_count_in_notification


@pytest.mark.parametrize(
    "template_class",
    [
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ],
)
@pytest.mark.parametrize(
    "content, values, expected_count_in_template, expected_count_in_notification",
    [
        # is an unsupported unicode character so should be replaced with a ?
        ("深", {}, 1, 1),
        # is a supported unicode character so should be kept as is
        ("Ŵ", {}, 1, 1),
        ("'First line.\n", {}, 12, 12),
        ("\t\n\r", {}, 0, 0),
        ("Content with ((placeholder))", {"placeholder": "something extra here"}, 13, 33),
        ("Content with ((placeholder))", {"placeholder": ""}, 13, 12),
        ("Just content", {}, 12, 12),
        ("((placeholder))  ", {"placeholder": "  "}, 0, 0),
        ("  ", {}, 0, 0),
        ("  G      D       S  ", {}, 5, 5),  # Becomes `G D S`
        ("P1 \n\n\n\n\n\n P2", {}, 6, 6),  # Becomes `P1\n\nP2`
    ],
)
def test_character_count_for_broadcast_templates(
    content, values, expected_count_in_template, expected_count_in_notification, template_class
):
    template = template_class(
        {"content": content, "template_type": "broadcast"},
    )
    assert template.content_count == expected_count_in_template
    template.values = values
    assert template.content_count == expected_count_in_notification


@pytest.mark.parametrize(
    "template_class",
    (
        SMSMessageTemplate,
        BroadcastMessageTemplate,
    ),
)
@pytest.mark.parametrize(
    "msg, expected_sms_fragment_count",
    [
        ("à" * 71, 1),  # welsh character in GSM
        ("à" * 160, 1),
        ("à" * 161, 2),
        ("à" * 306, 2),
        ("à" * 307, 3),
        ("à" * 612, 4),
        ("à" * 613, 5),
        ("à" * 765, 5),
        ("à" * 766, 6),
        ("à" * 918, 6),
        ("à" * 919, 7),
        ("ÿ" * 70, 1),  # welsh character not in GSM, so send as unicode
        ("ÿ" * 71, 2),
        ("ÿ" * 134, 2),
        ("ÿ" * 135, 3),
        ("ÿ" * 268, 4),
        ("ÿ" * 269, 5),
        ("ÿ" * 402, 6),
        ("ÿ" * 403, 7),
        ("à" * 70 + "ÿ", 2),  # just one non-gsm character means it's sent at unicode
        ("🚀" * 160, 1),  # non-welsh unicode characters are downgraded to gsm, so are only one fragment long
    ],
)
def test_sms_fragment_count_accounts_for_unicode_and_welsh_characters(
    template_class,
    msg,
    expected_sms_fragment_count,
):
    template = template_class({"content": msg, "template_type": template_class.template_type})
    assert template.fragment_count == expected_sms_fragment_count


@pytest.mark.parametrize(
    "template_class",
    (
        SMSMessageTemplate,
        BroadcastMessageTemplate,
    ),
)
@pytest.mark.parametrize(
    "msg, expected_sms_fragment_count",
    [
        # all extended GSM characters
        ("^" * 81, 2),
        # GSM characters plus extended GSM
        ("a" * 158 + "|", 1),
        ("a" * 159 + "|", 2),
        ("a" * 304 + "[", 2),
        ("a" * 304 + "[]", 3),
        # Welsh character plus extended GSM
        ("â" * 132 + "{", 2),
        ("â" * 133 + "}", 3),
    ],
)
def test_sms_fragment_count_accounts_for_extended_gsm_characters(
    template_class,
    msg,
    expected_sms_fragment_count,
):
    template = template_class({"content": msg, "template_type": template_class.template_type})
    assert template.fragment_count == expected_sms_fragment_count


@pytest.mark.parametrize(
    "template_class",
    [
        SMSMessageTemplate,
        SMSPreviewTemplate,
    ],
)
@pytest.mark.parametrize(
    "content, values, prefix, expected_result",
    [
        ("", {}, None, True),
        ("", {}, "GDS", True),
        ("((placeholder))", {"placeholder": ""}, "GDS", True),
        ("((placeholder))", {"placeholder": "Some content"}, None, False),
        ("Some content", {}, "GDS", False),
    ],
)
def test_is_message_empty_sms_templates(content, values, prefix, expected_result, template_class):
    template = template_class(
        {"content": content, "template_type": "sms"},
        prefix=prefix,
    )
    template.sender = None
    template.values = values
    assert template.is_message_empty() == expected_result


@pytest.mark.parametrize(
    "template_class",
    [
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ],
)
@pytest.mark.parametrize(
    "content, values, expected_result",
    [
        ("", {}, True),
        ("((placeholder))", {"placeholder": ""}, True),
        ("((placeholder))", {"placeholder": "Some content"}, False),
        ("Some content", {}, False),
    ],
)
def test_is_message_empty_broadcast_templates(content, values, expected_result, template_class):
    template = template_class(
        {"content": content, "template_type": "broadcast"},
    )
    template.sender = None
    template.values = values
    assert template.is_message_empty() == expected_result


@pytest.mark.parametrize(
    "template_class, template_type, extra_args, expected_field_calls",
    [
        (
            SMSMessageTemplate,
            "sms",
            {},
            [
                mock.call("content"),  # This is to get the placeholders
                mock.call("content", {}, html="passthrough"),
            ],
        ),
        (
            SMSPreviewTemplate,
            "sms",
            {},
            [
                mock.call("((phone number))", {}, with_brackets=False, html="escape"),
                mock.call("content", {}, html="escape", redact_missing_personalisation=False),
            ],
        ),
        (
            BroadcastMessageTemplate,
            "broadcast",
            {},
            [
                mock.call("content", {}, html="escape"),
            ],
        ),
        (
            BroadcastPreviewTemplate,
            "broadcast",
            {},
            [
                mock.call("((phone number))", {}, with_brackets=False, html="escape"),
                mock.call("content", {}, html="escape", redact_missing_personalisation=False),
            ],
        ),
        (
            SMSPreviewTemplate,
            "sms",
            {"redact_missing_personalisation": True},
            [
                mock.call("((phone number))", {}, with_brackets=False, html="escape"),
                mock.call("content", {}, html="escape", redact_missing_personalisation=True),
            ],
        ),
        (
            BroadcastPreviewTemplate,
            "broadcast",
            {"redact_missing_personalisation": True},
            [
                mock.call("((phone number))", {}, with_brackets=False, html="escape"),
                mock.call("content", {}, html="escape", redact_missing_personalisation=True),
            ],
        ),
    ],
)
@mock.patch("emergency_alerts_utils.template.Field.__init__", return_value=None)
@mock.patch("emergency_alerts_utils.template.Field.__str__", return_value="1\n2\n3\n4\n5\n6\n7\n8")
def test_templates_handle_html_and_redacting(
    mock_field_str,
    mock_field_init,
    template_class,
    template_type,
    extra_args,
    expected_field_calls,
):
    assert str(
        template_class({"content": "content", "subject": "subject", "template_type": template_type}, **extra_args)
    )
    assert mock_field_init.call_args_list == expected_field_calls


@pytest.mark.parametrize(
    "template_class, template_type, extra_args, expected_remove_whitespace_calls",
    [
        (
            SMSMessageTemplate,
            "sms",
            {},
            [
                mock.call("content"),
            ],
        ),
        (
            SMSPreviewTemplate,
            "sms",
            {},
            [
                mock.call("content"),
            ],
        ),
        (
            BroadcastMessageTemplate,
            "broadcast",
            {},
            [
                mock.call("content"),
            ],
        ),
        (
            BroadcastPreviewTemplate,
            "broadcast",
            {},
            [
                mock.call("content"),
            ],
        ),
    ],
)
@mock.patch("emergency_alerts_utils.template.remove_whitespace_before_punctuation", side_effect=lambda x: x)
def test_templates_remove_whitespace_before_punctuation(
    mock_remove_whitespace,
    template_class,
    template_type,
    extra_args,
    expected_remove_whitespace_calls,
):
    template = template_class(
        {"content": "content", "subject": "subject", "template_type": template_type}, **extra_args
    )

    assert str(template)

    if hasattr(template, "subject"):
        assert template.subject

    assert mock_remove_whitespace.call_args_list == expected_remove_whitespace_calls


@pytest.mark.parametrize(
    "template_class, template_type, extra_args, expected_calls",
    [
        (SMSMessageTemplate, "sms", {}, []),
        (SMSPreviewTemplate, "sms", {}, []),
        (BroadcastMessageTemplate, "broadcast", {}, []),
        (BroadcastPreviewTemplate, "broadcast", {}, []),
    ],
)
@mock.patch("emergency_alerts_utils.template.make_quotes_smart", side_effect=lambda x: x)
@mock.patch("emergency_alerts_utils.template.replace_hyphens_with_en_dashes", side_effect=lambda x: x)
def test_templates_make_quotes_smart_and_dashes_en(
    mock_en_dash_replacement,
    mock_smart_quotes,
    template_class,
    template_type,
    extra_args,
    expected_calls,
):
    template = template_class(
        {"content": "content", "subject": "subject", "template_type": template_type}, **extra_args
    )

    assert str(template)

    if hasattr(template, "subject"):
        assert template.subject

    mock_smart_quotes.assert_has_calls(expected_calls)
    mock_en_dash_replacement.assert_has_calls(expected_calls)


@pytest.mark.parametrize(
    "template_instance, expected_placeholders",
    [
        (
            SMSMessageTemplate(
                {"content": "((content))", "subject": "((subject))", "template_type": "sms"},
            ),
            ["content"],
        ),
        (
            SMSPreviewTemplate(
                {"content": "((content))", "subject": "((subject))", "template_type": "sms"},
            ),
            ["content"],
        ),
        (
            BroadcastMessageTemplate(
                {"content": "((content))", "subject": "((subject))", "template_type": "broadcast"},
            ),
            ["content"],
        ),
        (
            BroadcastPreviewTemplate(
                {"content": "((content))", "subject": "((subject))", "template_type": "broadcast"},
            ),
            ["content"],
        ),
    ],
)
def test_templates_extract_placeholders(
    template_instance,
    expected_placeholders,
):
    assert template_instance.placeholders == OrderedSet(expected_placeholders)


@pytest.mark.parametrize(
    "template_class",
    [
        SMSMessageTemplate,
        SMSPreviewTemplate,
    ],
)
def test_message_too_long_ignoring_prefix(template_class):
    body = ("b" * 917) + "((foo))"
    template = template_class(
        {"content": body, "template_type": template_class.template_type}, prefix="a" * 100, values={"foo": "cc"}
    )
    # content length is prefix + 919 characters (more than limit of 918)
    assert template.is_message_too_long() is True


@pytest.mark.parametrize(
    "template_class",
    [
        SMSMessageTemplate,
        SMSPreviewTemplate,
    ],
)
def test_message_is_not_too_long_ignoring_prefix(template_class):
    body = ("b" * 917) + "((foo))"
    template = template_class(
        {"content": body, "template_type": template_class.template_type},
        prefix="a" * 100,
        values={"foo": "c"},
    )
    # content length is prefix + 918 characters (not more than limit of 918)
    assert template.is_message_too_long() is False


@pytest.mark.parametrize(
    "extra_characters, expected_too_long",
    (
        ("cc", True),  # content length is 919 characters (more than limit of 918)
        ("c", False),  # content length is 918 characters (not more than limit of 918)
    ),
)
@pytest.mark.parametrize(
    "template_class",
    [
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ],
)
def test_broadcast_message_too_long(template_class, extra_characters, expected_too_long):
    body = ("b" * 917) + "((foo))"
    template = template_class({"content": body, "template_type": "broadcast"}, values={"foo": extra_characters})
    assert template.is_message_too_long() is expected_too_long


@pytest.mark.parametrize(
    "content",
    (
        ("The     quick brown fox.\n" "\n\n\n\n" "Jumps over the lazy dog.   \n" "Single linebreak above."),
        (
            "\n   \n"
            "The quick brown fox.  \n\n"
            "          Jumps over the lazy dog   .  \n"
            "Single linebreak above. \n  \n \n"
        ),
    ),
)
@pytest.mark.parametrize(
    "template_class, expected",
    (
        (SMSMessageTemplate, ("The quick brown fox.\n" "\n" "Jumps over the lazy dog.\n" "Single linebreak above.")),
        (
            SMSPreviewTemplate,
            (
                "\n\n"
                '<div class="sms-message-wrapper">\n'
                "  The quick brown fox.<br><br>Jumps over the lazy dog.<br>Single linebreak above.\n"
                "</div>"
            ),
        ),
        (
            BroadcastPreviewTemplate,
            (
                '<div class="broadcast-message-wrapper">\n'
                '  <h2 class="broadcast-message-heading">\n'
                '    <svg class="broadcast-message-heading__icon" '
                'xmlns="http://www.w3.org/2000/svg" width="22" height="18.23" '
                'viewBox="0 0 17.5 14.5" aria-hidden="true">\n'
                '      <path fill-rule="evenodd"\n'
                '            fill="currentcolor"\n'
                '            d="M8.6 0L0 14.5h17.5L8.6 0zm.2 10.3c-.8 0-1.5.7-1.5 1.5s.7 1.5 1.5 1.5 1.5-.7 '
                "1.5-1.5c-.1-.8-.7-1.5-1.5-1.5zm1.3-4.5c.1.8-.3 3.2-.3 3.2h-2s-.5-2.3-.5-3c0 0 0-1.6 1.4-1.6s1.4 "
                '1.4 1.4 1.4z"\n'
                "      />\n"
                "    </svg>\n"
                "    Emergency alert\n"
                "  </h2>\n"
                "  The quick brown fox.<br><br>Jumps over the lazy dog.<br>Single linebreak above.\n"
                "</div>"
            ),
        ),
    ),
)
def test_text_messages_collapse_consecutive_whitespace(
    template_class,
    content,
    expected,
):
    template = template_class({"content": content, "template_type": template_class.template_type})
    assert str(template) == expected
    assert (
        template.content_count
        == 70
        == len("The quick brown fox.\n" "\n" "Jumps over the lazy dog.\n" "Single linebreak above.")
    )


def test_broadcast_message_from_content():
    template = BroadcastMessageTemplate.from_content("test content")

    assert isinstance(template, BroadcastMessageTemplate)
    assert str(template) == "test content"


def test_broadcast_message_from_event():
    event = {
        "transmitted_content": {"body": "test content"},
    }
    template = BroadcastMessageTemplate.from_event(event)

    assert isinstance(template, BroadcastMessageTemplate)
    assert str(template) == "test content"


@pytest.mark.parametrize(
    "template_class",
    (
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ),
)
@pytest.mark.parametrize(
    "content, expected_non_gsm, expected_max, expected_too_long",
    (
        (
            "a" * 1395,
            set(),
            1395,
            False,
        ),
        (
            "a" * 1396,
            set(),
            1395,
            True,
        ),
        (
            "ŵ" * 615,
            {"ŵ"},
            615,
            False,
        ),
        (
            # Using a non-GSM character reduces the max content count
            "ŵ" * 616,
            {"ŵ"},
            615,
            True,
        ),
        (
            "[" * 697,  # Half of 1395, rounded down
            set(),
            1395,
            False,
        ),
        (
            "[" * 698,  # Half of 1395, rounded up
            set(),
            1395,
            True,
        ),
        (
            # In USC2 extended GSM characters are not double counted
            "ŵ]" * 307,
            {"ŵ"},
            615,
            False,
        ),
    ),
)
def test_broadcast_message_content_count(content, expected_non_gsm, expected_max, expected_too_long, template_class):
    template = template_class(
        {
            "template_type": "broadcast",
            "content": content,
        }
    )
    assert template.non_gsm_characters == expected_non_gsm
    assert template.max_content_count == expected_max
    assert template.content_too_long is expected_too_long


@pytest.mark.parametrize(
    "template_class",
    (
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ),
)
@pytest.mark.parametrize("content", ("^{}\\[~]|€"))
def test_broadcast_message_double_counts_extended_gsm(
    content,
    template_class,
):
    template = template_class(
        {
            "template_type": "broadcast",
            "content": content,
        }
    )
    assert template.encoded_content_count == 2
    assert template.max_content_count == 1_395


@pytest.mark.parametrize(
    "template_class",
    (
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ),
)
@pytest.mark.parametrize("content", ("ÁÍÓÚẂÝ" "ËÏẄŸ" "ÂÊÎÔÛŴŶ" "ÀÈÌÒẀÙỲ" "áíóúẃý" "ëïẅÿ" "âêîôûŵŷ" "ẁỳ"))
def test_broadcast_message_single_counts_diacritics_in_extended_gsm(
    content,
    template_class,
):
    template = template_class(
        {
            "template_type": "broadcast",
            "content": content,
        }
    )
    assert template.encoded_content_count == 1
    assert template.max_content_count == 615


@pytest.mark.parametrize(
    "template_class",
    (
        BroadcastMessageTemplate,
        BroadcastPreviewTemplate,
    ),
)
@pytest.mark.parametrize("content", ("ÄÖÜ" "É" "äöü" "é" "àèìòù"))
def test_broadcast_message_single_counts_diacritics_in_gsm(
    content,
    template_class,
):
    template = template_class(
        {
            "template_type": "broadcast",
            "content": content,
        }
    )
    assert template.encoded_content_count == 1
    assert template.max_content_count == 1_395
