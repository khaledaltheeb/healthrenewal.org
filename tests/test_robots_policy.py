from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from robots_policy import RobotsPolicyError, is_path_allowed, parse_robots, validate_robots_policy

AGENTS = ("OAI-SearchBot", "GPTBot")
SITEMAPS = (
    "https://healthrenewal.org/sitemap.xml",
    "https://healthrenewal.org/sitemap-index.xml",
)


class RobotsPolicyTests(unittest.TestCase):
    def validate(self, text: str, *, explicit: bool = True):
        return validate_robots_policy(
            text,
            required_agents=AGENTS,
            required_paths=("/", "/feed.xml", "/api/v1/content-index.json"),
            required_sitemaps=SITEMAPS,
            require_explicit_agents=explicit,
        )

    def test_adjacent_agent_and_rule(self) -> None:
        self.validate(
            "User-agent: OAI-SearchBot\nAllow: /\n\n"
            "User-agent: GPTBot\nAllow: /\n\n"
            "Sitemap: https://healthrenewal.org/sitemap.xml\n"
            "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
        )

    def test_blank_lines_comments_and_case_do_not_change_meaning(self) -> None:
        self.validate(
            "USER-AGENT: OAI-SearchBot\n\n# note\nALLOW: /\n\n"
            "User-Agent: GPTBot\n# another note\nAllow: /\n"
            "Sitemap: https://healthrenewal.org/sitemap.xml\n\n"
            "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
        )

    def test_multiple_agents_can_share_one_group(self) -> None:
        self.validate(
            "User-agent: GPTBot\nUser-agent: OAI-SearchBot\nAllow: /\n"
            "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
            "Sitemap: https://healthrenewal.org/sitemap.xml\n"
        )

    def test_group_order_does_not_change_meaning(self) -> None:
        self.validate(
            "User-agent: GPTBot\nAllow: /\n"
            "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
            "User-agent: OAI-SearchBot\nAllow: /\n"
            "Sitemap: https://healthrenewal.org/sitemap.xml\n"
        )

    def test_wildcard_is_valid_effective_fallback_when_explicit_not_required(self) -> None:
        self.validate(
            "User-agent: *\nAllow: /\n"
            "Sitemap: https://healthrenewal.org/sitemap.xml\n"
            "Sitemap: https://healthrenewal.org/sitemap-index.xml\n",
            explicit=False,
        )

    def test_missing_required_agent_fails_explicit_contract(self) -> None:
        with self.assertRaisesRegex(RobotsPolicyError, "GPTBot: missing explicit"):
            self.validate(
                "User-agent: OAI-SearchBot\nAllow: /\n"
                "User-agent: *\nAllow: /\n"
                "Sitemap: https://healthrenewal.org/sitemap.xml\n"
                "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
            )

    def test_disallow_root_fails(self) -> None:
        with self.assertRaisesRegex(RobotsPolicyError, "OAI-SearchBot: blocked required path /"):
            self.validate(
                "User-agent: OAI-SearchBot\nDisallow: /\n"
                "User-agent: GPTBot\nAllow: /\n"
                "Sitemap: https://healthrenewal.org/sitemap.xml\n"
                "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
            )

    def test_more_specific_rule_can_block_required_machine_path(self) -> None:
        with self.assertRaisesRegex(RobotsPolicyError, "blocked required path /api/v1/content-index.json"):
            self.validate(
                "User-agent: OAI-SearchBot\nAllow: /\nDisallow: /api/\n"
                "User-agent: GPTBot\nAllow: /\n"
                "Sitemap: https://healthrenewal.org/sitemap.xml\n"
                "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
            )

    def test_wildcard_path_rule_is_evaluated_semantically(self) -> None:
        policy = parse_robots("User-agent: GPTBot\nAllow: /\nDisallow: /private/*/draft$\n")
        self.assertFalse(is_path_allowed(policy, "GPTBot", "/private/a/draft"))
        self.assertTrue(is_path_allowed(policy, "GPTBot", "/private/a/draft-more"))

    def test_rule_under_another_agent_does_not_apply(self) -> None:
        policy = parse_robots(
            "User-agent: OAI-SearchBot\nDisallow: /private/\n"
            "User-agent: GPTBot\nAllow: /\n"
        )
        self.assertFalse(is_path_allowed(policy, "OAI-SearchBot", "/private/x"))
        self.assertTrue(is_path_allowed(policy, "GPTBot", "/private/x"))

    def test_duplicate_explicit_groups_fail(self) -> None:
        with self.assertRaisesRegex(RobotsPolicyError, "OAI-SearchBot: duplicate explicit"):
            self.validate(
                "User-agent: OAI-SearchBot\nAllow: /\n"
                "User-agent: GPTBot\nAllow: /\n"
                "User-agent: OAI-SearchBot\nDisallow: /private/\n"
                "Sitemap: https://healthrenewal.org/sitemap.xml\n"
                "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
            )

    def test_duplicate_required_sitemap_fails_semantically(self) -> None:
        with self.assertRaisesRegex(RobotsPolicyError, "must appear exactly once; found 2"):
            self.validate(
                "User-agent: OAI-SearchBot\nUser-agent: GPTBot\nAllow: /\n"
                "Sitemap: https://healthrenewal.org/sitemap.xml\n"
                "Sitemap: https://healthrenewal.org/sitemap.xml # duplicate\n"
                "Sitemap: https://healthrenewal.org/sitemap-index.xml\n"
            )


if __name__ == "__main__":
    unittest.main()
