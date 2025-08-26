import pytest

from emergency_alerts_utils.validation import (
    InvalidEmailError,
    InvalidPhoneError,
    allowed_to_send_to,
    format_phone_number_human_readable,
    format_recipient,
    is_uk_phone_number,
    normalise_phone_number,
    try_validate_and_format_phone_number,
    validate_and_format_phone_number,
    validate_email_address,
    validate_phone_number,
)

valid_uk_phone_numbers = [
    "7123456789",
    "07123456789",
    "07123 456789",
    "07123-456-789",
    "00447123456789",
    "00 44 7123456789",
    "+447123456789",
    "+44 7123 456 789",
    "+44 (0)7123 456 789",
    "\u200b\t\t+44 (0)7123 \ufeff 456 789 \r\n",
]


valid_international_phone_numbers = [
    "71234567890",  # Russia
    "1-202-555-0104",  # USA
    "+12025550104",  # USA
    "0012025550104",  # USA
    "+0012025550104",  # USA
    "23051234567",  # Mauritius,
    "+682 12345",  # Cook islands
    "+3312345678",
    "003312345678",
    "1-2345-12345-12345",  # 15 digits
]


valid_phone_numbers = valid_uk_phone_numbers + valid_international_phone_numbers


invalid_uk_phone_numbers = sum(
    [
        [(phone_number, error) for phone_number in group]
        for error, group in [
            (
                "Too many digits",
                (
                    "712345678910",
                    "0712345678910",
                    "0044712345678910",
                    "0044712345678910",
                    "+44 (0)7123 456 789 10",
                ),
            ),
            (
                "Not enough digits",
                (
                    "0712345678",
                    "004471234567",
                    "00447123456",
                    "+44 (0)7123 456 78",
                ),
            ),
            (
                "Not a UK mobile number",
                (
                    "08081 570364",
                    "+44 8081 570364",
                    "0117 496 0860",
                    "+44 117 496 0860",
                    "020 7946 0991",
                    "+44 20 7946 0991",
                ),
            ),
            (
                "Must not contain letters or symbols",
                (
                    "07890x32109",
                    "07123 456789...",
                    "07123 ☟☜⬇⬆☞☝",
                    "07123☟☜⬇⬆☞☝",
                    '07";DROP TABLE;"',
                    "+44 07ab cde fgh",
                    "ALPHANUM3R1C",
                ),
            ),
        ]
    ],
    [],
)


invalid_phone_numbers = list(
    filter(
        lambda number: number[0]
        not in {
            "712345678910",  # Could be Russia
        },
        invalid_uk_phone_numbers,
    )
) + [
    ("800000000000", "Not a valid country prefix"),
    ("1234567", "Not enough digits"),
    ("+682 1234", "Not enough digits"),  # Cook Islands phone numbers can be 5 digits
    ("+12345 12345 12345 6", "Too many digits"),
]


valid_email_addresses = (
    "email@domain.com",
    "email@domain.COM",
    "firstname.lastname@domain.com",
    "firstname.o'lastname@domain.com",
    "email@subdomain.domain.com",
    "firstname+lastname@domain.com",
    "1234567890@domain.com",
    "email@domain-one.com",
    "_______@domain.com",
    "email@domain.name",
    "email@domain.superlongtld",
    "email@domain.co.jp",
    "firstname-lastname@domain.com",
    "info@german-financial-services.vermögensberatung",
    "info@german-financial-services.reallylongarbitrarytldthatiswaytoohugejustincase",
    "japanese-info@例え.テスト",
    "email@double--hyphen.com",
)
invalid_email_addresses = (
    "email@123.123.123.123",
    "email@[123.123.123.123]",
    "plainaddress",
    "@no-local-part.com",
    "Outlook Contact <outlook-contact@domain.com>",
    "no-at.domain.com",
    "no-tld@domain",
    ";beginning-semicolon@domain.co.uk",
    "middle-semicolon@domain.co;uk",
    "trailing-semicolon@domain.com;",
    '"email+leading-quotes@domain.com',
    'email+middle"-quotes@domain.com',
    '"quoted-local-part"@domain.com',
    '"quoted@domain.com"',
    "lots-of-dots@domain..gov..uk",
    "two-dots..in-local@domain.com",
    "multiple@domains@domain.com",
    "spaces in local@domain.com",
    "spaces-in-domain@dom ain.com",
    "underscores-in-domain@dom_ain.com",
    "pipe-in-domain@example.com|gov.uk",
    "comma,in-local@gov.uk",
    "comma-in-domain@domain,gov.uk",
    "pound-sign-in-local£@domain.com",
    "local-with-’-apostrophe@domain.com",
    "local-with-”-quotes@domain.com",
    "domain-starts-with-a-dot@.domain.com",
    "brackets(in)local@domain.com",
    f"email-too-long-{'a' * 320}@example.com",
    "incorrect-punycode@xn---something.com",
)


@pytest.mark.parametrize("phone_number", valid_international_phone_numbers)
def test_detect_international_phone_numbers(phone_number):
    assert is_uk_phone_number(phone_number) is False


@pytest.mark.parametrize("phone_number", valid_uk_phone_numbers)
def test_detect_uk_phone_numbers(phone_number):
    assert is_uk_phone_number(phone_number) is True


@pytest.mark.parametrize(
    "phone_number",
    [
        "abcd",
        "079OO900123",
        pytest.param("", marks=pytest.mark.xfail),
        pytest.param("12345", marks=pytest.mark.xfail),
        pytest.param("+12345", marks=pytest.mark.xfail),
        pytest.param("1-2-3-4-5", marks=pytest.mark.xfail),
        pytest.param("1 2 3 4 5", marks=pytest.mark.xfail),
        pytest.param("(1)2345", marks=pytest.mark.xfail),
    ],
)
def test_normalise_phone_number_raises_if_unparseable_characters(phone_number):
    with pytest.raises(InvalidPhoneError):
        normalise_phone_number(phone_number)


@pytest.mark.parametrize("phone_number", valid_uk_phone_numbers)
@pytest.mark.parametrize(
    "extra_args",
    [
        {},
        {"international": False},
    ],
)
def test_phone_number_accepts_valid_values(extra_args, phone_number):
    try:
        validate_phone_number(phone_number, **extra_args)
    except InvalidPhoneError:
        pytest.fail("Unexpected InvalidPhoneError")


@pytest.mark.parametrize("phone_number", valid_uk_phone_numbers)
def test_valid_uk_phone_number_can_be_formatted_consistently(phone_number):
    assert validate_and_format_phone_number(phone_number) == "447123456789"


@pytest.mark.parametrize("phone_number, error_message", invalid_uk_phone_numbers)
@pytest.mark.parametrize(
    "extra_args",
    [
        {},
        {"international": False},
    ],
)
def test_phone_number_rejects_invalid_values(extra_args, phone_number, error_message):
    with pytest.raises(InvalidPhoneError) as e:
        validate_phone_number(phone_number, **extra_args)
    assert error_message == str(e.value)


@pytest.mark.parametrize("email_address", valid_email_addresses)
def test_validate_email_address_accepts_valid(email_address):
    try:
        assert validate_email_address(email_address) == email_address
    except InvalidEmailError:
        pytest.fail("Unexpected InvalidEmailError")


@pytest.mark.parametrize(
    "email",
    [
        " email@domain.com ",
        "\temail@domain.com",
        "\temail@domain.com\n",
        "\u200bemail@domain.com\u200b",
    ],
)
def test_validate_email_address_strips_whitespace(email):
    assert validate_email_address(email) == "email@domain.com"


@pytest.mark.parametrize("email_address", invalid_email_addresses)
def test_validate_email_address_raises_for_invalid(email_address):
    with pytest.raises(InvalidEmailError) as e:
        validate_email_address(email_address)
    assert str(e.value) == "Not a valid email address"


@pytest.mark.parametrize("phone_number", valid_uk_phone_numbers)
def test_validates_against_guestlist_of_phone_numbers(phone_number):
    assert allowed_to_send_to(phone_number, ["07123456789", "07700900460", "test@example.com"])
    assert not allowed_to_send_to(phone_number, ["07700900460", "07700900461", "test@example.com"])


@pytest.mark.parametrize("email_address", valid_email_addresses)
def test_validates_against_guestlist_of_email_addresses(email_address):
    assert not allowed_to_send_to(email_address, ["very_special_and_unique@example.com"])


@pytest.mark.parametrize(
    "phone_number, expected_formatted",
    [
        ("07900900123", "07900 900123"),  # UK
        ("+44(0)7900900123", "07900 900123"),  # UK
        ("447900900123", "07900 900123"),  # UK
    ],
)
def test_format_uk_and_international_phone_numbers(phone_number, expected_formatted):
    assert format_phone_number_human_readable(phone_number) == expected_formatted


@pytest.mark.parametrize(
    "recipient, expected_formatted",
    [
        (True, ""),
        (False, ""),
        (0, ""),
        (0.1, ""),
        (None, ""),
        ("foo", "foo"),
        ("TeSt@ExAmPl3.com", "test@exampl3.com"),
        ("+4407900 900 123", "447900900123"),
    ],
)
def test_format_recipient(recipient, expected_formatted):
    assert format_recipient(recipient) == expected_formatted


def test_try_format_recipient_doesnt_throw():
    assert try_validate_and_format_phone_number("ALPHANUM3R1C") == "ALPHANUM3R1C"


def test_format_phone_number_human_readable_doenst_throw():
    assert format_phone_number_human_readable("ALPHANUM3R1C") == "ALPHANUM3R1C"
