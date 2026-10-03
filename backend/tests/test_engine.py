"""Tests for Role B's text-masking engine.

Run from the repository root with:
    python -m unittest backend.tests.test_engine -v
"""

import re
import unittest
from unittest.mock import patch

from backend import engine
from backend.rules.base import Rule


def make_rule(
    type_name: str,
    pattern: str,
    replacement: str,
    chars_masked: int,
    priority: int = 1,
    near_miss: str | None = None,
) -> Rule:
    """Create a small predictable rule for testing engine behavior."""

    def mask(match: re.Match) -> tuple[str, int]:
        return replacement, chars_masked

    return Rule(
        type=type_name,
        pattern=re.compile(pattern),
        mask=mask,
        near_miss=re.compile(near_miss) if near_miss is not None else None,
        priority=priority,
    )


class EngineTests(unittest.TestCase):
    def mask_with_rules(self, rules: list[Rule], text: str, types: list[str] | None = None) -> dict:
        with patch.object(engine, "RULES", rules):
            return engine.mask_text(text, types)

    def test_empty_text_returns_original_and_zero_summary(self):
        result = self.mask_with_rules([], "")

        self.assertEqual(
            result,
            {
                "ok": True,
                "original_text": "",
                "masked_text": "",
                "detections": [],
                "errors": [],
                "summary": {
                    "total_detections": 0,
                    "total_chars_masked": 0,
                    "total_errors": 0,
                    "by_type": {
                        "credit_card": {"count": 0, "chars_masked": 0, "errors": 0},
                        "email": {"count": 0, "chars_masked": 0, "errors": 0},
                        "phone": {"count": 0, "chars_masked": 0, "errors": 0},
                        "dob": {"count": 0, "chars_masked": 0, "errors": 0},
                        "address": {"count": 0, "chars_masked": 0, "errors": 0},
                    },
                },
            },
        )

    def test_nonempty_text_without_matches_is_preserved(self):
        text = "ordinary text with no matching values"

        result = self.mask_with_rules([], text)

        self.assertEqual(result["original_text"], text)
        self.assertEqual(result["masked_text"], text)
        self.assertEqual(result["detections"], [])
        self.assertEqual(result["errors"], [])

    def test_none_types_runs_every_rule_and_adjacent_matches_are_kept(self):
        late_rule = make_rule("email", r"B", "X", 1, priority=5)
        early_rule = make_rule("credit_card", r"A", "X", 1, priority=1)

        result = self.mask_with_rules([late_rule, early_rule], "AB")

        self.assertEqual(result["masked_text"], "XX")
        self.assertEqual(
            [detection["type"] for detection in result["detections"]],
            ["credit_card", "email"],
        )
        self.assertEqual([detection["id"] for detection in result["detections"]], [0, 1])
        self.assertEqual(
            [detection["original"] for detection in result["detections"]],
            [
                {"start": 0, "end": 1, "text": "A"},
                {"start": 1, "end": 2, "text": "B"},
            ],
        )

    def test_types_filters_rules_and_unknown_or_empty_types_do_nothing(self):
        card_rule = make_rule("credit_card", r"1234", "XXXX", 4)
        email_rule = make_rule("email", r"user@example\.com", "u***@example.com", 3)

        result = self.mask_with_rules(
            [card_rule, email_rule], "1234 user@example.com", types=["email"]
        )

        self.assertEqual(result["masked_text"], "1234 u***@example.com")
        self.assertEqual([detection["type"] for detection in result["detections"]], ["email"])
        self.assertEqual(
            result["summary"]["by_type"]["credit_card"],
            {"count": 0, "chars_masked": 0, "errors": 0},
        )

        for types in ([], ["not_a_supported_type"]):
            with self.subTest(types=types):
                result = self.mask_with_rules(
                    [card_rule, email_rule], "1234 user@example.com", types=types
                )
                self.assertEqual(result["masked_text"], "1234 user@example.com")
                self.assertEqual(result["detections"], [])
                self.assertEqual(result["errors"], [])

    def test_higher_priority_match_wins_when_ranges_overlap(self):
        lower_priority = make_rule("credit_card", r"1234", "XXXX", 4, priority=1)
        higher_priority = make_rule("phone", r"234", "XXX", 3, priority=2)

        result = self.mask_with_rules([lower_priority, higher_priority], "1234")

        self.assertEqual(result["masked_text"], "1XXX")
        self.assertEqual(
            result["detections"],
            [
                {
                    "id": 0,
                    "type": "phone",
                    "original": {"start": 1, "end": 4, "text": "234"},
                    "masked": {"start": 1, "end": 4, "text": "XXX"},
                    "chars_masked": 3,
                }
            ],
        )

    def test_longer_mask_updates_offsets_for_following_detection(self):
        # Role C's current card rule accepts dashed cards. This fake rule tests
        # the engine contract where a 16-character match becomes 19 characters.
        card_rule = make_rule(
            "credit_card",
            r"(?<!\d)\d{16}(?!\d)",
            "XXXX-XXXX-XXXX-3456",
            12,
            priority=3,
        )
        phone_rule = make_rule("phone", r"(?<!\d)555(?!\d)", "XXX", 3, priority=2)
        text = "Card 1234567890123456; phone 555"

        result = self.mask_with_rules([card_rule, phone_rule], text)

        self.assertEqual(result["masked_text"], "Card XXXX-XXXX-XXXX-3456; phone XXX")
        card_detection, phone_detection = result["detections"]
        card_start = text.index("1234567890123456")
        phone_start = text.index("555")
        self.assertEqual(
            card_detection["original"],
            {"start": card_start, "end": card_start + 16, "text": "1234567890123456"},
        )
        self.assertEqual(
            card_detection["masked"],
            {"start": card_start, "end": card_start + 19, "text": "XXXX-XXXX-XXXX-3456"},
        )
        self.assertEqual(phone_detection["original"]["start"], phone_start)
        self.assertEqual(phone_detection["masked"]["start"], phone_start + 3)
        for detection in result["detections"]:
            original = detection["original"]
            masked = detection["masked"]
            self.assertEqual(text[original["start"] : original["end"]], original["text"])
            self.assertEqual(
                result["masked_text"][masked["start"] : masked["end"]], masked["text"]
            )

    def test_near_miss_errors_are_reported_but_valid_matches_are_not(self):
        phone_rule = make_rule(
            "phone",
            r"\d{3}-\d{3}",
            "XXX-XXX",
            6,
            near_miss=r"\d{3}-\d{3}|\d{6}",
        )
        text = "valid 123-456; invalid 789012"

        result = self.mask_with_rules([phone_rule], text)

        self.assertEqual(result["masked_text"], "valid XXX-XXX; invalid 789012")
        self.assertEqual(len(result["detections"]), 1)
        start = text.index("789012")
        self.assertEqual(
            result["errors"],
            [
                {
                    "type": "phone",
                    "code": "INVALID_FORMAT",
                    "message": "Possible phone has an invalid format.",
                    "original": {"start": start, "end": start + 6, "text": "789012"},
                }
            ],
        )

    def test_none_near_miss_is_skipped_and_inactive_rules_do_not_report_errors(self):
        card_rule = make_rule("credit_card", r"\d{4}", "XXXX", 4)
        phone_rule = make_rule(
            "phone", r"\d{3}-\d{3}", "XXX-XXX", 6, near_miss=r"\d{6}"
        )

        result = self.mask_with_rules([card_rule, phone_rule], "123456", types=["credit_card"])

        self.assertEqual(result["masked_text"], "XXXX56")
        self.assertEqual(result["errors"], [])

    def test_summary_counts_detections_masked_characters_and_errors_by_type(self):
        email_rule = make_rule("email", r"e\d", "**", 2, near_miss=r"e\d|bad")
        address_rule = make_rule("address", r"a\d", "X", 1, near_miss=r"bad")

        result = self.mask_with_rules([email_rule, address_rule], "e1 bad a2 bad")

        summary = result["summary"]
        self.assertEqual(summary["total_detections"], 2)
        self.assertEqual(summary["total_chars_masked"], 3)
        self.assertEqual(summary["total_errors"], 4)
        self.assertEqual(
            summary["by_type"]["email"], {"count": 1, "chars_masked": 2, "errors": 2}
        )
        self.assertEqual(
            summary["by_type"]["address"], {"count": 1, "chars_masked": 1, "errors": 2}
        )
        self.assertEqual(
            summary["by_type"]["phone"], {"count": 0, "chars_masked": 0, "errors": 0}
        )

    def test_real_rules_can_be_used_through_engine(self):
        from backend.rules import RULES

        text = "Email: somchai.d@company.com; Phone: 093-245-7894"
        result = self.mask_with_rules(RULES, text, types=["email", "phone"])

        self.assertEqual(
            result["masked_text"], "Email: s*******d@company.com; Phone: XXX-XXX-7894"
        )
        self.assertEqual(
            [detection["type"] for detection in result["detections"]], ["email", "phone"]
        )
        self.assertEqual(result["errors"], [])

    def test_real_rules_mask_all_five_supported_types(self):
        from backend.rules import RULES

        text = "\n".join(
            [
                "Credit card: 1234-5678-9012-3456",
                "Email: somchai.d@company.com",
                "Phone: 093-245-7894",
                "DOB:25/12/2549",
                "Address: 99/123 ถนนสุขุมวิท",
            ]
        )

        result = self.mask_with_rules(RULES, text)

        self.assertEqual(
            result["masked_text"],
            "\n".join(
                [
                    "Credit card: XXXX-XXXX-XXXX-3456",
                    "Email: s*******d@company.com",
                    "Phone: XXX-XXX-7894",
                    "DOB:XX/XX/25XX",
                    "Address: XX/XXX ถนนสุขุมวิท",
                ]
            ),
        )
        self.assertEqual(
            [detection["type"] for detection in result["detections"]],
            ["credit_card", "email", "phone", "dob", "address"],
        )
        self.assertEqual(result["summary"]["total_chars_masked"], 36)
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
