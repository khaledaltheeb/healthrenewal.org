#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit
import re

_RULE_FIELDS = {"allow", "disallow"}


class RobotsPolicyError(ValueError):
    """Raised when a robots.txt policy violates a required crawler contract."""


@dataclass(frozen=True)
class RobotsGroup:
    agents: tuple[str, ...]
    rules: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class RobotsPolicy:
    groups: tuple[RobotsGroup, ...]
    sitemaps: tuple[str, ...]

    def explicit_groups_for(self, agent: str) -> tuple[RobotsGroup, ...]:
        target = agent.casefold()
        return tuple(
            group
            for group in self.groups
            if any(candidate.casefold() == target for candidate in group.agents)
        )

    def effective_groups_for(self, agent: str) -> tuple[RobotsGroup, ...]:
        explicit = self.explicit_groups_for(agent)
        if explicit:
            return explicit
        return tuple(
            group
            for group in self.groups
            if any(candidate == "*" for candidate in group.agents)
        )


def parse_robots(text: str) -> RobotsPolicy:
    """Parse robots.txt into semantic user-agent groups and global sitemaps.

    Blank lines and comments are formatting only. Consecutive User-agent fields
    before rules belong to the same group, as defined by the robots exclusion
    protocol. Directive names are case-insensitive; values are preserved.
    """

    groups: list[RobotsGroup] = []
    sitemaps: list[str] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append(RobotsGroup(tuple(agents), tuple(rules)))
        agents = []
        rules = []

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.casefold()

        if field == "sitemap":
            if value:
                sitemaps.append(value)
            continue

        if field == "user-agent":
            if not value:
                raise RobotsPolicyError(f"line {number}: empty User-agent")
            if agents and rules:
                flush()
            agents.append(value.casefold())
            continue

        if field in _RULE_FIELDS:
            if not agents:
                raise RobotsPolicyError(
                    f"line {number}: {field.title()} directive has no User-agent group"
                )
            rules.append((field, value))

    flush()
    return RobotsPolicy(tuple(groups), tuple(sitemaps))


def _path_pattern_matches(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    anchored = pattern.endswith("$")
    if anchored:
        pattern = pattern[:-1]
    expression = re.escape(pattern).replace(r"\*", ".*")
    expression = "^" + expression + ("$" if anchored else "")
    return re.match(expression, path) is not None


def _rule_specificity(pattern: str) -> int:
    return len(pattern.replace("*", "").rstrip("$"))


def is_path_allowed(policy: RobotsPolicy, agent: str, path: str) -> bool:
    """Return the effective robots decision for an agent/path pair.

    Explicit groups win over wildcard groups. For matching rules, the longest
    path pattern wins; Allow wins ties. Absence of a matching rule means allow.
    """

    if not path.startswith("/"):
        path = urlsplit(path).path or "/"
    groups = policy.effective_groups_for(agent)
    if not groups:
        return True

    matches: list[tuple[int, int, str, str]] = []
    for group in groups:
        for field, pattern in group.rules:
            if field == "disallow" and pattern == "":
                continue
            if _path_pattern_matches(pattern, path):
                matches.append(
                    (_rule_specificity(pattern), 1 if field == "allow" else 0, field, pattern)
                )
    if not matches:
        return True
    _, _, field, _ = max(matches, key=lambda item: (item[0], item[1]))
    return field == "allow"


def validate_robots_policy(
    text: str,
    *,
    required_agents: tuple[str, ...] = (),
    required_paths: tuple[str, ...] = ("/",),
    required_sitemaps: tuple[str, ...] = (),
    require_explicit_agents: bool = False,
) -> RobotsPolicy:
    """Validate crawler access semantically and return the parsed policy."""

    policy = parse_robots(text)

    for agent in required_agents:
        explicit = policy.explicit_groups_for(agent)
        if len(explicit) > 1:
            raise RobotsPolicyError(
                f"{agent}: duplicate explicit User-agent groups ({len(explicit)})"
            )
        if require_explicit_agents and not explicit:
            raise RobotsPolicyError(f"{agent}: missing explicit User-agent policy")
        if not policy.effective_groups_for(agent):
            raise RobotsPolicyError(f"{agent}: no explicit or wildcard policy")
        for path in required_paths:
            if not is_path_allowed(policy, agent, path):
                raise RobotsPolicyError(f"{agent}: blocked required path {path}")

    sitemap_counts: dict[str, int] = {}
    for sitemap in policy.sitemaps:
        sitemap_counts[sitemap] = sitemap_counts.get(sitemap, 0) + 1
    for sitemap in required_sitemaps:
        count = sitemap_counts.get(sitemap, 0)
        if count != 1:
            raise RobotsPolicyError(
                f"Sitemap {sitemap!r} must appear exactly once; found {count}"
            )

    return policy
