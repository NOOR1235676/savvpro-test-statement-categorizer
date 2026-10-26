from app.categorizer import Txn, categorize


def t(desc, amt):
    return Txn("2026-01-01", desc, amt)


def test_software():
    assert categorize(t("ADOBE CREATIVE CLOUD", -20)).category == "Software"


def test_transfer():
    assert categorize(t("TRANSFER TO SAVINGS", -500)).category == "Transfer"


def test_refund_is_not_income():
    assert categorize(t("UBER *TRIP REFUND", 12)).category == "Refund"


def test_cafe_with_reference_number():
    assert categorize(t("JOES CAFE 9921x", -9)).category == "Meals"


def test_unknown_goes_to_review():
    r = categorize(t("XYZ TRADERS 1234", -50))
    assert r.needs_review and r.category == "Needs Review"


def test_unknown_credit_goes_to_review():
    assert categorize(t("DEPOSIT 8899", 100)).needs_review


def test_memory_overrides_rules():
    r = categorize(t("JOES STORE 9921", -5), {"JOES STORE": "Meals"})
    assert r.category == "Meals" and r.confidence == 1.0


def test_short_keyword_needs_whole_word():
    assert categorize(t("PIANO LESSONS", -30)).needs_review


def test_income_source():
    assert categorize(t("PAYONEER PAYOUT", 500)).category == "Income"


def test_ambiguous_goes_to_review():
    assert categorize(t("UBER KFC", -10)).needs_review
