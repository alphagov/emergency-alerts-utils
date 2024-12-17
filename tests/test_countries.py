import pytest

from emergency_alerts_utils.countries import (
    Country,
    CountryMapping,
    CountryNotFoundError,
)
from emergency_alerts_utils.countries.data import (
    _UK_ISLANDS_LIST,
    ADDITIONAL_SYNONYMS,
    COUNTRIES_AND_TERRITORIES,
    UK,
    UK_ISLANDS,
    WELSH_NAMES,
)

from .country_synonyms import ALL as ALL_SYNONYMS
from .country_synonyms import CROWDSOURCED_MISTAKES


def test_constants():
    assert UK == "United Kingdom"
    assert UK_ISLANDS == [
        ("Alderney", UK),
        ("Brecqhou", UK),
        ("Guernsey", UK),
        ("Herm", UK),
        ("Isle of Man", UK),
        ("Jersey", UK),
        ("Jethou", UK),
        ("Sark", UK),
    ]


@pytest.mark.parametrize("synonym, canonical", ADDITIONAL_SYNONYMS)
def test_hand_crafted_synonyms_map_to_canonical_countries(synonym, canonical):
    synonyms = dict(COUNTRIES_AND_TERRITORIES).keys()
    canonical_names = list(dict(COUNTRIES_AND_TERRITORIES).values())

    assert canonical in (canonical_names + _UK_ISLANDS_LIST)

    assert synonym not in {CountryMapping.make_key(synonym_) for synonym_ in synonyms}
    assert Country(synonym).canonical_name == canonical


@pytest.mark.parametrize("welsh_name, canonical", WELSH_NAMES)
def test_welsh_names_map_to_canonical_countries(welsh_name, canonical):
    assert Country(canonical).canonical_name == canonical
    assert Country(welsh_name).canonical_name == canonical


def test_all_synonyms():
    for search, expected in ALL_SYNONYMS:
        assert Country(search).canonical_name == expected


def test_crowdsourced_test_data():
    for search, expected_country in CROWDSOURCED_MISTAKES:
        if expected_country:
            assert Country(search).canonical_name == expected_country


@pytest.mark.parametrize(
    "search, expected",
    (
        ("UK", "United Kingdom"),
        ("England", "United Kingdom"),
        ("Northern Ireland", "United Kingdom"),
        ("Scotland", "United Kingdom"),
        ("Wales", "United Kingdom"),
        ("N. Ireland", "United Kingdom"),
        ("GB", "United Kingdom"),
        ("NIR", "United Kingdom"),
        ("SCT", "United Kingdom"),
        ("WLS", "United Kingdom"),
        ("Jersey", "United Kingdom"),
        ("Guernsey", "United Kingdom"),
    ),
)
def test_hand_crafted_synonyms(search, expected):
    assert Country(search).canonical_name == expected


def test_auto_checking_for_country_starting_with_the():
    canonical_names = dict(COUNTRIES_AND_TERRITORIES).values()
    synonyms = dict(COUNTRIES_AND_TERRITORIES).keys()
    assert "The Gambia" in canonical_names
    assert "Gambia" not in synonyms
    assert Country("Gambia").canonical_name == "The Gambia"


@pytest.mark.parametrize(
    "search, expected_error_message",
    (
        ("Qumran", "Not a known country or territory (Qumran)"),
        ("Kumrahn", "Not a known country or territory (Kumrahn)"),
    ),
)
def test_non_existant_countries(search, expected_error_message):
    with pytest.raises(KeyError) as error:
        Country(search)
    assert str(error.value) == repr(expected_error_message)
    assert isinstance(error.value, CountryNotFoundError)
