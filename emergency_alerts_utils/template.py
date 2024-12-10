import math
from abc import ABC, abstractmethod
from functools import lru_cache
from os import path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from emergency_alerts_utils import MAGIC_SEQUENCE, SMS_CHAR_COUNT_LIMIT
from emergency_alerts_utils.field import Field, PlainTextField
from emergency_alerts_utils.formatters import (
    add_prefix,
    autolink_urls,
    escape_html,
    make_quotes_smart,
    nl2br,
    normalise_multiple_newlines,
    normalise_whitespace_and_newlines,
    remove_smart_quotes_from_email_addresses,
    remove_whitespace_before_punctuation,
    replace_hyphens_with_en_dashes,
    sms_encode,
)
from emergency_alerts_utils.insensitive_dict import InsensitiveDict
from emergency_alerts_utils.sanitise_text import SanitiseSMS
from emergency_alerts_utils.take import Take
from emergency_alerts_utils.template_change import TemplateChange

template_env = Environment(
    loader=FileSystemLoader(
        path.join(
            path.dirname(path.abspath(__file__)),
            "jinja_templates",
        )
    )
)

MAX_BROADCAST_CHAR_COUNT = 1395


class Template(ABC):
    def __init__(
        self,
        template,
        values=None,
        redact_missing_personalisation=False,
    ):
        if not isinstance(template, dict):
            raise TypeError("Template must be a dict")
        if values is not None and not isinstance(values, dict):
            raise TypeError("Values must be a dict")
        if template.get("template_type") != self.template_type:
            raise TypeError(
                f"Cannot initialise {self.__class__.__name__} " f'with {template.get("template_type")} template_type'
            )
        self.id = template.get("id", None)
        self.name = template.get("name", None)
        self.content = template["content"]
        self.values = values
        self._template = template
        self.redact_missing_personalisation = redact_missing_personalisation

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.content}", {self.values})'

    @abstractmethod
    def __str__(self):
        pass

    @property
    def content_with_placeholders_filled_in(self):
        return str(
            Field(
                self.content,
                self.values,
                html="passthrough",
                redact_missing_personalisation=self.redact_missing_personalisation,
                markdown_lists=True,
            )
        ).strip()

    @property
    def values(self):
        if hasattr(self, "_values"):
            return self._values
        return {}

    @values.setter
    def values(self, value):
        if not value:
            self._values = {}
        else:
            placeholders = InsensitiveDict.from_keys(self.placeholders)
            self._values = InsensitiveDict(value).as_dict_with_keys(
                self.placeholders
                | set(key for key in value.keys() if InsensitiveDict.make_key(key) not in placeholders.keys())
            )

    @property
    def placeholders(self):
        return get_placeholders(self.content)

    @property
    def missing_data(self):
        return list(placeholder for placeholder in self.placeholders if self.values.get(placeholder) is None)

    @property
    def additional_data(self):
        return self.values.keys() - self.placeholders

    def get_raw(self, key, default=None):
        return self._template.get(key, default)

    def compare_to(self, new):
        return TemplateChange(self, new)

    @property
    def content_count(self):
        return len(self.content_with_placeholders_filled_in)

    def is_message_empty(self):
        if not self.content:
            return True

        if not self.content.startswith("((") or not self.content.endswith("))"):
            # If the content doesn’t start or end with a placeholder we
            # can guarantee it’s not empty, no matter what
            # personalisation has been provided.
            return False

        return self.content_count == 0

    def is_message_too_long(self):
        return False


class BaseSMSTemplate(Template):
    template_type = "sms"

    def __init__(
        self,
        template,
        values=None,
        prefix=None,
        show_prefix=True,
        sender=None,
    ):
        self.prefix = prefix
        self.show_prefix = show_prefix
        self.sender = sender
        self._content_count = None
        super().__init__(template, values)

    @property
    def values(self):
        return super().values

    @values.setter
    def values(self, value):
        # If we change the values of the template it’s possible the
        # content count will have changed, so we need to reset the
        # cached count.
        if self._content_count is not None:
            self._content_count = None

        # Assigning to super().values doesn’t work here. We need to get
        # the property object instead, which has the special method
        # fset, which invokes the setter it as if we were
        # assigning to it outside this class.
        super(BaseSMSTemplate, type(self)).values.fset(self, value)

    @property
    def content_with_placeholders_filled_in(self):
        # We always call SMSMessageTemplate.__str__ regardless of
        # subclass, to avoid any HTML formatting. SMS templates differ
        # in that the content can include the service name as a prefix.
        # So historically we’ve returned the fully-formatted message,
        # rather than some plain-text represenation of the content. To
        # preserve compatibility for consumers of the API we maintain
        # that behaviour by overriding this method here.
        return SMSMessageTemplate.__str__(self)

    @property
    def prefix(self):
        return self._prefix if self.show_prefix else None

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    @property
    def content_count(self):
        """
        Return the number of characters in the message. Note that we don't distinguish between GSM and non-GSM
        characters at this point, as `get_sms_fragment_count` handles that separately.

        Also note that if values aren't provided, will calculate the raw length of the unsubstituted placeholders,
        as in the message `foo ((placeholder))` has a length of 19.
        """
        if self._content_count is None:
            self._content_count = len(self._get_unsanitised_content())
        return self._content_count

    @property
    def content_count_without_prefix(self):
        # subtract 2 extra characters to account for the colon and the space,
        # added max zero in case the content is empty the __str__ methods strips the white space.
        if self.prefix:
            return max((self.content_count - len(self.prefix) - 2), 0)
        else:
            return self.content_count

    @property
    def fragment_count(self):
        content_with_placeholders = str(self)

        # Extended GSM characters count as 2 characters
        character_count = self.content_count + count_extended_gsm_chars(content_with_placeholders)

        return get_sms_fragment_count(character_count, non_gsm_characters(content_with_placeholders))

    def is_message_too_long(self):
        """
        Message is validated with out the prefix.
        We have decided to be lenient and let the message go over the character limit. The SMS provider will
        send messages well over our limit. There were some inconsistencies with how we were validating the
        length of a message. This should be the method used anytime we want to reject a message for being too long.
        """
        return self.content_count_without_prefix > SMS_CHAR_COUNT_LIMIT

    def is_message_empty(self):
        return self.content_count_without_prefix == 0

    def _get_unsanitised_content(self):
        # This is faster to call than SMSMessageTemplate.__str__ if all
        # you need to know is how many characters are in the message
        if self.values:
            values = self.values
        else:
            values = {key: MAGIC_SEQUENCE for key in self.placeholders}
        return (
            Take(PlainTextField(self.content, values, html="passthrough"))
            .then(add_prefix, self.prefix)
            .then(remove_whitespace_before_punctuation)
            .then(normalise_whitespace_and_newlines)
            .then(normalise_multiple_newlines)
            .then(str.strip)
            .then(str.replace, MAGIC_SEQUENCE, "")
        )


class SMSMessageTemplate(BaseSMSTemplate):
    def __str__(self):
        return sms_encode(self._get_unsanitised_content())


class SMSPreviewTemplate(BaseSMSTemplate):
    jinja_template = template_env.get_template("sms_preview_template.jinja2")

    def __init__(
        self,
        template,
        values=None,
        prefix=None,
        show_prefix=True,
        sender=None,
        show_recipient=False,
        show_sender=False,
        downgrade_non_sms_characters=True,
        redact_missing_personalisation=False,
    ):
        self.show_recipient = show_recipient
        self.show_sender = show_sender
        self.downgrade_non_sms_characters = downgrade_non_sms_characters
        super().__init__(template, values, prefix, show_prefix, sender)
        self.redact_missing_personalisation = redact_missing_personalisation

    def __str__(self):
        return Markup(
            self.jinja_template.render(
                {
                    "sender": self.sender,
                    "show_sender": self.show_sender,
                    "recipient": Field("((phone number))", self.values, with_brackets=False, html="escape"),
                    "show_recipient": self.show_recipient,
                    "body": Take(
                        Field(
                            self.content,
                            self.values,
                            html="escape",
                            redact_missing_personalisation=self.redact_missing_personalisation,
                        )
                    )
                    .then(add_prefix, (escape_html(self.prefix) or None) if self.show_prefix else None)
                    .then(sms_encode if self.downgrade_non_sms_characters else str)
                    .then(remove_whitespace_before_punctuation)
                    .then(normalise_whitespace_and_newlines)
                    .then(normalise_multiple_newlines)
                    .then(nl2br)
                    .then(
                        autolink_urls,
                        classes="govuk-link govuk-link--no-visited-state",
                    ),
                }
            )
        )


class BaseBroadcastTemplate(BaseSMSTemplate):
    template_type = "broadcast"

    MAX_CONTENT_COUNT_GSM = 1_395
    MAX_CONTENT_COUNT_UCS2 = 615

    @property
    def encoded_content_count(self):
        if self.non_gsm_characters:
            return self.content_count
        return self.content_count + count_extended_gsm_chars(self.content_with_placeholders_filled_in)

    @property
    def non_gsm_characters(self):
        return non_gsm_characters(self.content)

    @property
    def max_content_count(self):
        if self.non_gsm_characters:
            return self.MAX_CONTENT_COUNT_UCS2
        return self.MAX_CONTENT_COUNT_GSM

    @property
    def content_too_long(self):
        return self.encoded_content_count > self.max_content_count


class BroadcastPreviewTemplate(BaseBroadcastTemplate, SMSPreviewTemplate):
    jinja_template = template_env.get_template("broadcast_preview_template.jinja2")


class BroadcastMessageTemplate(BaseBroadcastTemplate, SMSMessageTemplate):
    @classmethod
    def from_content(cls, content):
        return cls(
            template={
                "template_type": cls.template_type,
                "content": content,
            },
            values=None,  # events have already done interpolation of any personalisation
        )

    @classmethod
    def from_event(cls, broadcast_event):
        """
        should be directly callable with the results of the BroadcastEvent.serialize() function from api/models.py
        """
        return cls.from_content(broadcast_event["transmitted_content"]["body"])

    def __str__(self):
        return (
            Take(
                Field(
                    self.content.strip(),
                    self.values,
                    html="escape",
                )
            )
            .then(sms_encode)
            .then(remove_whitespace_before_punctuation)
            .then(normalise_whitespace_and_newlines)
            .then(normalise_multiple_newlines)
        )


def get_sms_fragment_count(character_count, non_gsm_characters):
    if non_gsm_characters:
        return 1 if character_count <= 70 else math.ceil(float(character_count) / 67)
    else:
        return 1 if character_count <= 160 else math.ceil(float(character_count) / 153)


def non_gsm_characters(content):
    """
    Returns a set of all the non gsm characters in a text. this doesn't include characters that we will downgrade (eg
    emoji, ellipsis, ñ, etc). This only includes welsh non gsm characters that will force the entire SMS to be encoded
    with UCS-2.
    """
    return set(content) & set(SanitiseSMS.WELSH_NON_GSM_CHARACTERS)


def count_extended_gsm_chars(content):
    return sum(map(content.count, SanitiseSMS.EXTENDED_GSM_CHARACTERS))


def do_nice_typography(value):
    return (
        Take(value)
        .then(remove_whitespace_before_punctuation)
        .then(make_quotes_smart)
        .then(remove_smart_quotes_from_email_addresses)
        .then(replace_hyphens_with_en_dashes)
    )


@lru_cache(maxsize=1024)
def get_placeholders(content):
    return Field(content).placeholders
