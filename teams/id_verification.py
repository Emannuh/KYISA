"""
KYISA Teams — Player ID Verification Utilities

Provides stateless helpers for:
  - Kenya National ID format validation
  - Age eligibility checks against competition age groups
  - Duplicate player detection (by national_id_number or name+DOB)
  - A convenience wrapper that runs all checks in sequence

All helpers work against the current Player and CountyPlayer models.
TransferRequest and legacy field references have been removed.
"""

from datetime import date
import re

from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
#  ID FORMAT VALIDATION
# ---------------------------------------------------------------------------

class IDVerification:
    """Kenya National ID format validation."""

    @staticmethod
    def validate_kenyan_id(id_number: str) -> str:
        """
        Validate a Kenya National ID number.

        Accepted formats:
          - 8 digits: 12345678
          - Alphanumeric 7-12 chars (new-generation IDs): 12345678A

        Returns the normalised (uppercased, stripped) value on success.
        Raises ValidationError on failure.
        """
        if not id_number:
            raise ValidationError("National ID number is required.")

        cleaned = str(id_number).replace(" ", "").strip().upper()

        old_format = re.match(r"^\d{8}$", cleaned)
        new_format = re.match(r"^[A-Z0-9]{7,12}$", cleaned)

        if not (old_format or new_format):
            raise ValidationError(
                "Invalid National ID format. Expected 8 digits (e.g. 12345678) "
                "or 7–12 alphanumeric characters (e.g. 12345678A)."
            )
        return cleaned

    @staticmethod
    def check_age_eligibility(date_of_birth: date, min_age: int = 16, max_age: int = 35) -> int:
        """
        Confirm the player is within [min_age, max_age].

        Returns the player's age on success.
        Raises ValidationError if outside the bounds.
        """
        if not date_of_birth:
            raise ValidationError("Date of birth is required.")

        today = date.today()
        age = (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )

        if age < min_age:
            raise ValidationError(
                f"Player must be at least {min_age} years old (current age: {age})."
            )
        if age > max_age:
            raise ValidationError(
                f"Player cannot be older than {max_age} years (current age: {age})."
            )
        return age


# ---------------------------------------------------------------------------
#  DUPLICATE DETECTION
# ---------------------------------------------------------------------------

class DuplicatePlayerChecker:
    """
    Cross-team duplicate checks for the Player model (club teams) and
    CountyPlayer model (county squads).  Uses the correct field names
    (national_id_number, get_full_name(), team.name).
    """

    # ── Club players (teams.Player) ────────────────────────────────────────

    @staticmethod
    def check_id_number(id_number: str, exclude_player_id: int | None = None) -> bool:
        """
        Raise ValidationError if a Player with the given national_id_number
        already exists (excluding the player being edited).
        """
        from teams.models import Player

        qs = Player.objects.filter(national_id_number=id_number)
        if exclude_player_id:
            qs = qs.exclude(pk=exclude_player_id)

        if qs.exists():
            p = qs.select_related("team").first()
            raise ValidationError(
                f"A player with National ID {id_number} is already registered. "
                f"Name: {p.get_full_name()}, Team: {p.team.name}."
            )
        return True

    @staticmethod
    def check_duplicate_by_name_dob(
        first_name: str,
        last_name: str,
        date_of_birth: date,
        exclude_player_id: int | None = None,
    ) -> bool:
        """
        Raise ValidationError if a Player with the same name and DOB exists
        (case-insensitive).
        """
        from teams.models import Player

        qs = Player.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            date_of_birth=date_of_birth,
        )
        if exclude_player_id:
            qs = qs.exclude(pk=exclude_player_id)

        if qs.exists():
            p = qs.select_related("team").first()
            raise ValidationError(
                f"A player named {first_name} {last_name} with the same date of birth "
                f"already exists (Team: {p.team.name}, ID: {p.national_id_number or 'N/A'})."
            )
        return True

    # ── County players (teams.CountyPlayer) ───────────────────────────────

    @staticmethod
    def check_county_player_id(
        id_number: str,
        exclude_player_id: int | None = None,
    ) -> bool:
        """
        Raise ValidationError if a CountyPlayer with the given national_id_number
        already exists across any county or discipline.
        """
        from teams.models import CountyPlayer

        qs = CountyPlayer.objects.filter(national_id_number=id_number)
        if exclude_player_id:
            qs = qs.exclude(pk=exclude_player_id)

        if qs.exists():
            p = qs.select_related("discipline__registration").first()
            county = p.discipline.registration.county
            raise ValidationError(
                f"A county player with National ID {id_number} is already registered "
                f"under {county} — {p.get_full_name()}."
            )
        return True


# ---------------------------------------------------------------------------
#  FULL REGISTRATION VERIFICATION WORKFLOW
# ---------------------------------------------------------------------------

def verify_player_registration(player_data: dict) -> dict:
    """
    Run the full verification pipeline for a club Player registration.

    Expected keys in player_data:
        first_name, last_name, date_of_birth (date),
        national_id_number (str),
        exclude_player_id (int, optional — pass when editing an existing player)

    Returns a dict:
        {
            "valid": bool,
            "errors": [str, ...],
            "warnings": [str, ...],
            "age": int | None,
            "national_id_number": str | None,
        }

    Does NOT raise — all exceptions are caught and collected in "errors".
    """
    result: dict = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "age": None,
        "national_id_number": None,
    }

    exclude_id = player_data.get("exclude_player_id")

    try:
        # 1. Validate ID format
        clean_id = IDVerification.validate_kenyan_id(player_data.get("national_id_number", ""))
        result["national_id_number"] = clean_id
    except ValidationError as exc:
        result["valid"] = False
        result["errors"].append(str(exc.message))
        return result  # can't proceed without a valid ID

    try:
        # 2. Age eligibility (default 16–35; callers may override via separate call)
        age = IDVerification.check_age_eligibility(player_data["date_of_birth"])
        result["age"] = age
    except ValidationError as exc:
        result["valid"] = False
        result["errors"].append(str(exc.message))

    try:
        # 3. Duplicate ID check
        DuplicatePlayerChecker.check_id_number(clean_id, exclude_player_id=exclude_id)
    except ValidationError as exc:
        result["valid"] = False
        result["errors"].append(str(exc.message))

    try:
        # 4. Duplicate name+DOB check
        DuplicatePlayerChecker.check_duplicate_by_name_dob(
            player_data["first_name"],
            player_data["last_name"],
            player_data["date_of_birth"],
            exclude_player_id=exclude_id,
        )
    except ValidationError as exc:
        # Treat as a warning (same name/DOB could be a twin, etc.)
        result["warnings"].append(str(exc.message))

    return result


# ---------------------------------------------------------------------------
#  AGE CATEGORY HELPERS
# ---------------------------------------------------------------------------

AGE_CATEGORIES = {
    "U13":  {"min": 10, "max": 13, "name": "Under 13"},
    "U15":  {"min": 13, "max": 15, "name": "Under 15"},
    "U17":  {"min": 15, "max": 17, "name": "Under 17"},
    "U20":  {"min": 17, "max": 20, "name": "Under 20"},
    "U23":  {"min": 20, "max": 23, "name": "Under 23"},
    "OPEN": {"min": 16, "max": 45, "name": "Open Age"},
}


def get_player_age_category(date_of_birth: date) -> dict | None:
    """
    Return the age category dict for a player, or None if no category matches.

    Returns e.g. {"code": "U17", "name": "Under 17", "age": 16}
    """
    today = date.today()
    age = (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )

    for code, info in AGE_CATEGORIES.items():
        if info["min"] <= age <= info["max"]:
            return {"code": code, "name": info["name"], "age": age}

    return None
