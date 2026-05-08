import pytest
import tempfile
from pathlib import Path

from eventbot.prefs import (
    UserPrefs,
    Schedule,
    load_prefs,
    save_prefs,
    load_all_prefs,
    synthesize_household,
    HOUSEHOLD_SLUG,
)


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content)


def test_load_prefs(tmp_path: Path):
    yaml = tmp_path / "alice.yaml"
    yaml.write_text(
        "display_name: Alice\n"
        "email: alice@example.com\n"
        "location: Portland, OR\n"
        "timezone: America/Los_Angeles\n"
        "interests:\n  - live music\n  - hiking\n"
        "blocklist:\n  - country music\n"
        "schedule:\n  frequency: weekly\n  day_of_week: monday\n  day_of_month: 1\n  hour: 8\n"
    )
    prefs = load_prefs(yaml)
    assert prefs.slug == "alice"
    assert prefs.display_name == "Alice"
    assert "live music" in prefs.interests
    assert "country music" in prefs.blocklist
    assert prefs.schedule.frequency == "weekly"


def test_save_and_reload(tmp_path: Path):
    prefs = UserPrefs(
        slug="bob",
        display_name="Bob",
        email="bob@example.com",
        location="Seattle, WA",
        timezone="America/Los_Angeles",
        interests=["jazz", "hiking"],
        blocklist=["EDM"],
        schedule=Schedule(frequency="daily", hour=7),
    )
    path = tmp_path / "bob.yaml"
    save_prefs(prefs, path)
    reloaded = load_prefs(path)
    assert reloaded.display_name == "Bob"
    assert reloaded.interests == ["jazz", "hiking"]
    assert reloaded.schedule.frequency == "daily"


def test_load_all_prefs(tmp_path: Path):
    (tmp_path / "alice.yaml").write_text(
        "display_name: Alice\nemail: a@x.com\nlocation: Portland\ntimezone: UTC\n"
        "interests: []\nblocklist: []\nschedule:\n  frequency: weekly\n  day_of_week: monday\n  day_of_month: 1\n  hour: 8\n"
    )
    (tmp_path / "household.yaml").write_text(
        "display_name: Household\nemail: h@x.com\nlocation: Portland\ntimezone: UTC\n"
        "interests: []\nblocklist: []\nschedule:\n  frequency: weekly\n  day_of_week: tuesday\n  day_of_month: 1\n  hour: 9\n"
    )
    all_prefs = load_all_prefs(tmp_path)
    assert "alice" in all_prefs
    assert "household" in all_prefs
    assert all_prefs["household"].is_household is True
    assert all_prefs["alice"].is_household is False


def test_synthesize_household_union():
    alice = UserPrefs(
        slug="alice", display_name="Alice", email="a@x.com",
        location="Portland", timezone="America/Los_Angeles",
        interests=["live music", "hiking"], blocklist=["country"],
    )
    bob = UserPrefs(
        slug="bob", display_name="Bob", email="b@x.com",
        location="Portland", timezone="America/Los_Angeles",
        interests=["jazz", "hiking"], blocklist=["EDM"],
    )
    household = synthesize_household([alice, bob])
    assert "live music" in household.interests
    assert "jazz" in household.interests
    assert "hiking" in household.interests
    assert len([i for i in household.interests if i == "hiking"]) == 1  # deduped
    assert "country" in household.blocklist
    assert "EDM" in household.blocklist


def test_synthesize_preserves_existing_email():
    existing = UserPrefs(
        slug=HOUSEHOLD_SLUG, display_name="Household", email="family@example.com",
        location="Portland", timezone="UTC", is_household=True,
    )
    alice = UserPrefs(slug="alice", display_name="Alice", email="a@x.com",
                      location="Portland", timezone="UTC")
    result = synthesize_household([alice], existing=existing)
    assert result.email == "family@example.com"
