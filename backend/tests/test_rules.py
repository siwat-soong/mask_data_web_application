# Run from the repo root:  python -m pytest backend/tests -v
import pytest
from backend.rules import RULES, credit_card, email, phone, dob, address


def apply(rule, text):
    """Mask every match of one rule in text, the way the engine will."""
    return rule.pattern.sub(lambda m: rule.mask(m)[0], text)


# (rule, input, expected output)
SHOULD_MASK = [
    (credit_card.RULE, "1234-5678-9012-3456", "XXXX-XXXX-XXXX-3456"),
    (credit_card.RULE, "card 1234-5678-9012-3456 ok", "card XXXX-XXXX-XXXX-3456 ok"),
    (email.RULE, "somchai.d@company.com", "s*******d@company.com"),
    (email.RULE, "ติดต่อ somchai.d@company.co.th.", "ติดต่อ s*******d@company.co.th."),
    (phone.RULE, "093-245-7894", "XXX-XXX-7894"),
    (phone.RULE, "โทร 093-245-7894, 081-111-2222", "โทร XXX-XXX-7894, XXX-XXX-2222"),
    (dob.RULE, "DOB:25/12/2549", "DOB:XX/XX/25XX"),
    (dob.RULE, "DOB: 01/01/2500", "DOB: XX/XX/25XX"),
    (address.RULE, "Address: 689 ซอยลาดกระบัง 19 ถนนลาดกระบัง", "Address: XXX ซอยลาดกระบัง 19 ถนนลาดกระบัง"),
    (address.RULE, "Address: 99/123 ถนนสุขุมวิท", "Address: XX/XXX ถนนสุขุมวิท"),
]

# (rule, input) - the valid pattern must find nothing here
SHOULD_NOT_MATCH = [
    (credit_card.RULE, "1234-5678-9012-34567"),      # too many digits
    (credit_card.RULE, "1234-5678-9012"),            # only 3 groups
    (credit_card.RULE, "1234567890123456"),          # no dashes
    (email.RULE, "somchai.d@company"),               # no dot in the domain
    (email.RULE, "@company.com"),                    # no username
    (phone.RULE, "1234-5678-9012-3456"),             # a card is not a phone
    (phone.RULE, "0932457894"),                      # no dashes
    (dob.RULE, "DOB:25/13/2549"),                    # month 13
    (dob.RULE, "25/12/2549"),                        # no DOB: label
    (address.RULE, "Address: ซอยลาดกระบัง 19"),       # no house number
    (address.RULE, "ซอยลาดกระบัง 19"),                # no Address: label
]

# (rule, input) - invalid for the valid pattern, but caught by near_miss
NEAR_MISSES = [
    (credit_card.RULE, "1234 5678 9012 3456"),
    (credit_card.RULE, "1234567890123456"),
    (credit_card.RULE, "123456789012345"),
    (email.RULE, "somchai.d@company"),
    (phone.RULE, "0932457894"),
    (dob.RULE, "DOB:25/13/2549"),
    (dob.RULE, "DOB:25-12-2549"),
    (dob.RULE, "dob:25/12/2549"),
    (address.RULE, "Address: ซอยลาดกระบัง 19"),
    (address.RULE, "address: 689 ถนนลาดกระบัง"),
]


@pytest.mark.parametrize("rule, text, expected", SHOULD_MASK)
def test_should_mask(rule, text, expected):
    assert apply(rule, text) == expected


@pytest.mark.parametrize("rule, text", SHOULD_NOT_MATCH)
def test_should_not_match(rule, text):
    assert rule.pattern.search(text) is None


@pytest.mark.parametrize("rule, text", NEAR_MISSES)
def test_near_miss(rule, text):
    assert rule.pattern.search(text) is None
    assert rule.near_miss.search(text) is not None


def test_chars_masked_counts():
    m = email.RULE.pattern.search("somchai.d@company.com")
    assert email.RULE.mask(m) == ("s*******d@company.com", 7)

    m = address.RULE.pattern.search("Address: 99/123 ถนนสุขุมวิท")
    assert address.RULE.mask(m) == ("Address: XX/XXX", 5)


def test_short_email_username_is_left_as_is():
    assert apply(email.RULE, "ab@x.com") == "ab@x.com"


def test_match_positions():
    text = "call 093-245-7894 now"
    m = phone.RULE.pattern.search(text)
    assert (m.start(), m.end()) == (5, 17)
    assert text[m.start():m.end()] == "093-245-7894"


def test_registry_has_all_five_types():
    assert [r.type for r in RULES] == ["credit_card", "email", "phone", "dob", "address"]
