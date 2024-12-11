import re
from collections import namedtuple
from contextlib import suppress
from functools import lru_cache

import phonenumbers
from flask import current_app

from emergency_alerts_utils.formatters import (
    ALL_WHITESPACE,
    strip_and_remove_obscure_whitespace,
)

from . import EMAIL_REGEX_PATTERN, hostname_part, tld_part

uk_prefix = "44"

first_column_headings = {
    "email": ["email address"],
    "sms": ["phone number"],
}


class InvalidEmailError(Exception):
    def __init__(self, message=None):
        super().__init__(message or "Not a valid email address")


class InvalidPhoneError(InvalidEmailError):
    pass


class InvalidAddressError(InvalidEmailError):
    pass


def normalise_phone_number(number):
    for character in ALL_WHITESPACE + "()-+":
        number = number.replace(character, "")

    try:
        list(map(int, number))
    except ValueError:
        raise InvalidPhoneError("Must not contain letters or symbols")

    return number.lstrip("0")


def is_uk_phone_number(number):
    if number.startswith("0") and not number.startswith("00"):
        return True

    number = normalise_phone_number(number)

    if number.startswith(uk_prefix) or (number.startswith("7") and len(number) < 11):
        return True

    return False


international_phone_info = namedtuple(
    "PhoneNumber",
    [
        "international",
        "crown_dependency",
        "country_prefix",
    ],
)


def get_international_phone_info(number):
    number = validate_phone_number(number, international=True)
    prefix = get_international_prefix(number)
    crown_dependency = _is_a_crown_dependency_number(number)

    return international_phone_info(
        international=(prefix != uk_prefix or crown_dependency),
        crown_dependency=crown_dependency,
        country_prefix=prefix,
    )


CROWN_DEPENDENCY_RANGES = ["7781", "7839", "7911", "7509", "7797", "7937", "7700", "7829", "7624", "7524", "7924"]


def _is_a_crown_dependency_number(number):
    num_in_crown_dependency_range = number[2:6] in CROWN_DEPENDENCY_RANGES
    num_in_tv_range = number[2:9] == "7700900"

    return num_in_crown_dependency_range and not num_in_tv_range


COUNTRY_PREFIXES = ["44"]


def get_international_prefix(number):
    return next((prefix for prefix in COUNTRY_PREFIXES if number.startswith(prefix)), None)


def validate_uk_phone_number(number):
    number = normalise_phone_number(number).lstrip(uk_prefix).lstrip("0")

    if not number.startswith("7"):
        raise InvalidPhoneError("Not a UK mobile number")

    if len(number) > 10:
        raise InvalidPhoneError("Too many digits")

    if len(number) < 10:
        raise InvalidPhoneError("Not enough digits")

    return f"{uk_prefix}{number}"


def validate_phone_number(number, international=False):
    if (not international) or is_uk_phone_number(number):
        return validate_uk_phone_number(number)

    number = normalise_phone_number(number)

    if len(number) < 8:
        raise InvalidPhoneError("Not enough digits")

    if len(number) > 15:
        raise InvalidPhoneError("Too many digits")

    if get_international_prefix(number) is None:
        raise InvalidPhoneError("Not a valid country prefix")

    return number


validate_and_format_phone_number = validate_phone_number


def try_validate_and_format_phone_number(number, international=None, log_msg=None):
    """
    For use in places where you shouldn't error if the phone number is invalid - for example if firetext pass us
    something in
    """
    try:
        return validate_and_format_phone_number(number, international)
    except InvalidPhoneError as exc:
        if log_msg:
            current_app.logger.warning(f"{log_msg}: {exc}")
        return number


def validate_email_address(email_address):  # noqa (C901 too complex)
    # almost exactly the same as by https://github.com/wtforms/wtforms/blob/master/wtforms/validators.py,
    # with minor tweaks for SES compatibility - to avoid complications we are a lot stricter with the local part
    # than neccessary - we don't allow any double quotes or semicolons to prevent SES Technical Failures
    email_address = strip_and_remove_obscure_whitespace(email_address)
    match = re.match(EMAIL_REGEX_PATTERN, email_address)

    # not an email
    if not match:
        raise InvalidEmailError

    if len(email_address) > 320:
        raise InvalidEmailError

    # don't allow consecutive periods in either part
    if ".." in email_address:
        raise InvalidEmailError

    hostname = match.group(1)

    # idna = "Internationalized domain name" - this encode/decode cycle converts unicode into its accurate ascii
    # representation as the web uses. '例え.テスト'.encode('idna') == b'xn--r8jz45g.xn--zckzah'
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        raise InvalidEmailError

    parts = hostname.split(".")

    if len(hostname) > 253 or len(parts) < 2:
        raise InvalidEmailError

    for part in parts:
        if not part or len(part) > 63 or not hostname_part.match(part):
            raise InvalidEmailError

    # if the part after the last . is not a valid TLD then bail out
    if not tld_part.match(parts[-1]):
        raise InvalidEmailError

    return email_address


def format_email_address(email_address):
    return strip_and_remove_obscure_whitespace(email_address.lower())


def validate_and_format_email_address(email_address):
    return format_email_address(validate_email_address(email_address))


@lru_cache(maxsize=32, typed=False)
def format_recipient(recipient):
    if not isinstance(recipient, str):
        return ""
    with suppress(InvalidPhoneError):
        return validate_and_format_phone_number(recipient, international=True)
    with suppress(InvalidEmailError):
        return validate_and_format_email_address(recipient)
    return recipient


def format_phone_number_human_readable(phone_number):
    try:
        phone_number = validate_phone_number(phone_number, international=True)
    except InvalidPhoneError:
        # if there was a validation error, we want to shortcut out here, but still display the number on the front end
        return phone_number

    return phonenumbers.format_number(
        phonenumbers.parse("+" + phone_number, None),
        (phonenumbers.PhoneNumberFormat.NATIONAL),
    )


def allowed_to_send_to(recipient, allowlist):
    return format_recipient(recipient) in {format_recipient(x) for x in allowlist}


def insert_or_append_to_dict(dict_, key, value):
    if not (key or value):
        # We don’t care about completely empty values so it’s faster to
        # ignore them rather than working out how to store them
        return

    if dict_.get(key):
        if isinstance(dict_[key], list):
            dict_[key].append(value)
        else:
            dict_[key] = [dict_[key], value]
    else:
        dict_.update({key: value})
