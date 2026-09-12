from __future__ import annotations

from pathlib import Path

PROFILE_DIRECTORY = Path(__file__).resolve().parent / "profiles"
MARKER_PROFILE_PATHS = {
    "cheap-spell": PROFILE_DIRECTORY / "cheap_spell.py",
    "self-etb": PROFILE_DIRECTORY / "self_etb.py",
    "etb-payoff": PROFILE_DIRECTORY / "etb_payoff.py",
    "self-etb-creature": PROFILE_DIRECTORY / "self_etb_creature.py",
    "self-etb-artifact": PROFILE_DIRECTORY / "self_etb_artifact.py",
    "self-etb-enchantment": PROFILE_DIRECTORY / "self_etb_enchantment.py",
    "tutor-two-basic-lands": PROFILE_DIRECTORY / "tutor_two_basic_lands.py",
}
