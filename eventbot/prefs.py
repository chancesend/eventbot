from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator


HOUSEHOLD_SLUG = "household"


class Schedule(BaseModel):
    frequency: str = "weekly"   # daily | weekly | monthly
    day_of_week: str = "monday" # for weekly
    day_of_month: int = 1       # for monthly
    hour: int = 8               # local hour to run


class UserPrefs(BaseModel):
    slug: str
    display_name: str
    email: str
    location: str
    timezone: str = "America/New_York"
    interests: list[str] = []
    blocklist: list[str] = []
    schedule: Schedule = Schedule()
    is_household: bool = False

    @field_validator("interests", "blocklist", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> list:
        return v if isinstance(v, list) else []


def load_prefs(path: Path) -> UserPrefs:
    data = yaml.safe_load(path.read_text())
    slug = path.stem
    return UserPrefs(slug=slug, **data)


def save_prefs(prefs: UserPrefs, path: Path) -> None:
    data = prefs.model_dump(exclude={"slug", "is_household"})
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))


def load_all_prefs(prefs_dir: Path) -> dict[str, UserPrefs]:
    result: dict[str, UserPrefs] = {}
    for yaml_file in sorted(prefs_dir.glob("*.yaml")):
        prefs = load_prefs(yaml_file)
        if yaml_file.stem == HOUSEHOLD_SLUG:
            prefs.is_household = True
        result[prefs.slug] = prefs
    return result


def synthesize_household(
    user_prefs: list[UserPrefs],
    existing: UserPrefs | None = None,
) -> UserPrefs:
    """Build a household preference profile as the union of all user interests."""
    all_interests: list[str] = []
    all_blocklist: list[str] = []
    locations: list[str] = []

    for p in user_prefs:
        for interest in p.interests:
            if interest not in all_interests:
                all_interests.append(interest)
        for item in p.blocklist:
            if item not in all_blocklist:
                all_blocklist.append(item)
        if p.location and p.location not in locations:
            locations.append(p.location)

    return UserPrefs(
        slug=HOUSEHOLD_SLUG,
        display_name="Household",
        email=existing.email if existing else "",
        location=locations[0] if locations else "",
        timezone=existing.timezone if existing else (user_prefs[0].timezone if user_prefs else "UTC"),
        interests=all_interests,
        blocklist=all_blocklist,
        schedule=existing.schedule if existing else Schedule(),
        is_household=True,
    )
