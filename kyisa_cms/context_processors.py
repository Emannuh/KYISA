"""
KYISA — Portal Navigation Context Processor
============================================
Single source of truth for sidebar and bottom-nav items.
Each role gets a filtered list of NavItem objects; templates never
contain inline role chains.

A NavItem is a dataclass with:
  label        — display text
  icon         — Bootstrap Icons class  e.g. "bi bi-trophy"
  url_name     — Django URL name (or None for section headers)
  allowed_roles — tuple of role strings; empty tuple = all authenticated
  children     — list of child NavItems (for grouped sections)
  active_prefix — URL name substring that marks this item active
                  (defaults to url_name if not set)

The context processor exposes:
  portal_nav   — filtered list for the current user (honours role-preview)
  portal_role  — effective role string (after role-preview patch)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class NavItem:
    label: str
    icon: str
    url_name: Optional[str] = None
    allowed_roles: Tuple[str, ...] = ()        # empty = any authenticated
    children: List["NavItem"] = field(default_factory=list)
    active_prefix: Optional[str] = None        # falls back to url_name

    def is_active(self, current_url_name: str) -> bool:
        prefix = self.active_prefix or self.url_name or ""
        if prefix and prefix in (current_url_name or ""):
            return True
        return any(c.is_active(current_url_name) for c in self.children)


# ---------------------------------------------------------------------------
# Role constants (keep in sync with accounts.models.UserRole)
# ---------------------------------------------------------------------------
ADMIN               = "admin"
CM                  = "competition_manager"
SOCCER              = "soccer_coordinator"
HANDBALL            = "handball_coordinator"
BASKETBALL          = "basketball_coordinator"
VOLLEYBALL          = "volleyball_coordinator"
COORDINATOR         = "coordinator"            # legacy — kept for existing accounts
ALL_COORDINATORS    = (COORDINATOR, SOCCER, HANDBALL, BASKETBALL, VOLLEYBALL)
VO                  = "verification_officer"
REFEREE             = "referee"
TEAM_MANAGER        = "team_manager"
COUNTY_ADMIN        = "county_sports_admin"
CEC_SPORTS          = "cec_sports"
TREASURER           = "treasurer"
JURY                = "jury_chair"
MEDIA               = "media_manager"
SG                  = "secretary_general"
SCOUT               = "scout"
KICOSCA_OFFICER     = "kicosca_officer"
KICOSCA_SG          = "kicosca_sg"


# ---------------------------------------------------------------------------
# Navigation definition
# ---------------------------------------------------------------------------

def _nav_for_role(role: str) -> List[NavItem]:
    """Return the ordered nav sections for a given role."""

    # ── Shared snippets ──────────────────────────────────────────────────
    _media_items = [
        NavItem("Media Hub",    "bi bi-camera-reels", "media_dashboard",   active_prefix="media_dashboard"),
        NavItem("Articles",     "bi bi-newspaper",    "media_article_list",active_prefix="media_article"),
        NavItem("Photo Albums", "bi bi-images",       "media_album_list",  active_prefix="media_album"),
        NavItem("Videos",       "bi bi-play-circle",  "media_video_list",  active_prefix="media_video"),
        NavItem("Categories",   "bi bi-tags",         "media_categories",  active_prefix="media_categories"),
    ]

    # ── ADMIN ────────────────────────────────────────────────────────────
    if role == ADMIN:
        return [
            NavItem("Administration", "bi bi-shield-lock-fill", children=[
                NavItem("Control Centre", "bi bi-bar-chart-line",    "sys_admin_dashboard"),
                NavItem("User Management","bi bi-people-fill",       "manage_users"),
                NavItem("Activity Logs",  "bi bi-journal-text",      "activity_logs"),
                NavItem("Audit Report",   "bi bi-shield-check",      "audit_report"),
                NavItem("Email Centre",   "bi bi-envelope",          "email_logs",   active_prefix="email"),
            ]),
            NavItem("Competitions", "bi bi-trophy", children=[
                NavItem("All Competitions","bi bi-list-ul",           "competitions_list"),
                NavItem("Create New",      "bi bi-plus-circle",       "cm_create_competition"),
            ]),
            NavItem("Teams & Players", "bi bi-people", children=[
                NavItem("All Teams",          "bi bi-people",          "teams_list"),
                NavItem("County Registrations","bi bi-pencil-square",  "pending_teams"),
                NavItem("Player Verification", "bi bi-person-vcard",   "county_player_verification_list", active_prefix="county_player_verification"),
                NavItem("Squad Approval",      "bi bi-clipboard-check","squad_review_list"),
            ]),
            NavItem("Referees", "bi bi-flag", children=[
                NavItem("All Referees",    "bi bi-flag",          "referees_list"),
                NavItem("Pending Approval","bi bi-clock",         "pending_referees"),
                NavItem("Appointments",    "bi bi-calendar-event","referee_appointments"),
            ]),
            NavItem("Matches",   "bi bi-clipboard-data", "matches_list"),
            NavItem("Appeals",   "bi bi-briefcase",      "appeals_list"),
            NavItem("News & Media", "bi bi-newspaper", children=_media_items),
        ]

    # ── COMPETITION MANAGER ──────────────────────────────────────────────
    if role == CM:
        return [
            NavItem("Competitions", "bi bi-trophy", children=[
                NavItem("Dashboard",     "bi bi-speedometer2",  "cm_dashboard"),
                NavItem("All Competitions","bi bi-list-ul",     "competitions_list"),
                NavItem("Create New",    "bi bi-plus-circle",   "cm_create_competition"),
                NavItem("Venues",        "bi bi-geo-alt",       "cm_venues"),
                NavItem("Upload Players","bi bi-cloud-upload",  "cm_upload_players"),
            ]),
            NavItem("Teams & Players", "bi bi-people", children=[
                NavItem("All Teams",          "bi bi-people",         "teams_list"),
                NavItem("County Registrations","bi bi-pencil-square", "pending_teams"),
                NavItem("Player Verification", "bi bi-person-vcard",  "county_player_verification_list"),
                NavItem("Player Clearance",    "bi bi-shield-check",  "player_clearance_dashboard"),
            ]),
            NavItem("Referees", "bi bi-flag", children=[
                NavItem("All Referees",    "bi bi-flag",          "referees_list"),
                NavItem("Pending Approval","bi bi-clock",         "pending_referees"),
                NavItem("Appointments",    "bi bi-calendar-event","referee_appointments"),
            ]),
            NavItem("Matches", "bi bi-clipboard-data", "matches_list"),
            NavItem("News & Media", "bi bi-newspaper", children=_media_items),
        ]

    # ── ALL COORDINATORS (soccer, handball, basketball, volleyball, legacy) ──
    if role in ALL_COORDINATORS:
        return [
            NavItem("Coordinator Portal", "bi bi-clipboard2-pulse", children=[
                NavItem("Dashboard",       "bi bi-speedometer2",  "coordinator_dashboard"),
                NavItem("Competitions",    "bi bi-trophy",        "coordinator_competitions",  active_prefix="coordinator_competition"),
                NavItem("Appointments",    "bi bi-calendar-event","coordinator_appointments"),
                NavItem("Referees",        "bi bi-flag",          "coordinator_referees"),
                NavItem("Match Reports",   "bi bi-clipboard-data","coordinator_match_reports"),
                NavItem("Match Day Squads","bi bi-people",        "coordinator_squads"),
                NavItem("Venues",          "bi bi-geo-alt",       "coordinator_venues"),
            ]),
        ]

    # ── VERIFICATION OFFICER ─────────────────────────────────────────────
    if role == VO:
        return [
            NavItem("Verification", "bi bi-shield-check", children=[
                NavItem("Registered Counties","bi bi-geo-alt-fill",   "vo_registered_counties"),
                NavItem("All Players Queue",  "bi bi-list-check",     "county_player_verification_list"),
                NavItem("CEC Sports",         "bi bi-people-fill",    "cec_sports_portal"),
            ]),
        ]

    # ── REFEREE ──────────────────────────────────────────────────────────
    if role == REFEREE:
        return [
            NavItem("My Portal", "bi bi-flag", children=[
                NavItem("Dashboard",    "bi bi-bar-chart-line",   "referee_portal"),
                NavItem("My Profile",   "bi bi-person-gear",      "referee_edit_profile"),
                NavItem("Appointments", "bi bi-calendar-event",   "referees_list"),
                NavItem("Squad Approval","bi bi-clipboard-check", "squad_review_list"),
                NavItem("Match Reports","bi bi-file-earmark-text","matches_list"),
            ]),
        ]

    # ── TEAM MANAGER ─────────────────────────────────────────────────────
    if role == TEAM_MANAGER:
        return [
            NavItem("My Team", "bi bi-people", children=[
                NavItem("Dashboard",         "bi bi-speedometer2",        "team_manager_dashboard"),
                NavItem("My Team",           "bi bi-people",              "teams_list"),
                NavItem("Fixtures & Squads", "bi bi-clipboard-data",      "matches_list"),
            ]),
            NavItem("Disciplinary", "bi bi-exclamation-triangle", children=[
                NavItem("Sanctions",  "bi bi-exclamation-triangle","team_manager_sanctions"),
                NavItem("File Appeal","bi bi-briefcase",            "team_manager_file_appeal"),
                NavItem("My Appeals", "bi bi-list-ul",              "appeals_list"),
            ]),
        ]

    # ── COUNTY SPORTS DIRECTOR ───────────────────────────────────────────
    if role == COUNTY_ADMIN:
        return [
            NavItem("County Portal", "bi bi-building", children=[
                NavItem("Dashboard",         "bi bi-speedometer2",    "county_admin_dashboard"),
                NavItem("Payment",           "bi bi-credit-card",     "county_admin_payment"),
                NavItem("Disciplines",       "bi bi-trophy",          "county_admin_add_discipline"),
                NavItem("Delegation Members","bi bi-person-badge",    "county_admin_delegation_members"),
                NavItem("Verification Status","bi bi-shield-check",   "county_admin_verification"),
            ]),
        ]

    # ── CEC SPORTS MEMBER ────────────────────────────────────────────────
    if role == CEC_SPORTS:
        return [
            NavItem("CEC Sports", "bi bi-people-fill", children=[
                NavItem("Portal", "bi bi-people-fill", "cec_sports_portal"),
            ]),
        ]

    # ── TREASURER ────────────────────────────────────────────────────────
    if role == TREASURER:
        return [
            NavItem("Finance", "bi bi-cash-stack", children=[
                NavItem("Dashboard",              "bi bi-cash-stack",    "treasurer_dashboard"),
                NavItem("County Payments",        "bi bi-building",      "treasurer_county_payments"),
                NavItem("County Registrations",   "bi bi-person-badge",  "treasurer_county_registrations"),
                NavItem("Appeal Fees",            "bi bi-briefcase",     "appeals_list"),
            ]),
        ]

    # ── JURY CHAIR ───────────────────────────────────────────────────────
    if role == JURY:
        return [
            NavItem("Jury & Appeals", "bi bi-bank", children=[
                NavItem("Jury Dashboard","bi bi-bank",         "jury_dashboard"),
                NavItem("All Appeals",  "bi bi-briefcase",     "appeals_list"),
            ]),
            NavItem("Competition Data", "bi bi-trophy", children=[
                NavItem("Teams",         "bi bi-people-fill",         "jury_teams"),
                NavItem("Players",       "bi bi-person-check-fill",   "jury_players"),
                NavItem("Fixtures",      "bi bi-calendar-event",      "jury_fixtures"),
                NavItem("Match Reports", "bi bi-file-earmark-text",   "jury_match_reports"),
                NavItem("Squads",        "bi bi-list-check",          "jury_squads"),
                NavItem("Disciplinary",  "bi bi-exclamation-triangle-fill","jury_disciplinary"),
            ]),
        ]

    # ── SECRETARY GENERAL ────────────────────────────────────────────────
    if role == SG:
        return [
            NavItem("Oversight", "bi bi-shield-fill-check", children=[
                NavItem("Dashboard",         "bi bi-speedometer2",        "sg_dashboard"),
                NavItem("System Overview",   "bi bi-grid-3x3-gap-fill",   "sg_system_overview"),
                NavItem("Verifications",     "bi bi-person-vcard",        "sg_verifications"),
                NavItem("Appeals",           "bi bi-briefcase",           "sg_appeals"),
                NavItem("Treasurer Actions", "bi bi-cash-stack",          "sg_treasurer_actions"),
                NavItem("User Activity",     "bi bi-journal-text",        "sg_user_actions"),
                NavItem("Exceptional Overrides","bi bi-shield-exclamation","sg_exceptional_overrides"),
                NavItem("Verified Players",  "bi bi-patch-check-fill",    "sg_verified_players"),
                NavItem("Team Lists",        "bi bi-list-check",          "sg_team_lists"),
                NavItem("CEC Sports",        "bi bi-people-fill",         "cec_sports_portal"),
            ]),
            NavItem("Reports", "bi bi-bar-chart-line", children=[
                NavItem("Audit Report",  "bi bi-shield-check", "audit_report"),
                NavItem("Activity Logs", "bi bi-list-ul",      "activity_logs"),
                NavItem("Email Centre",  "bi bi-envelope",     "email_logs", active_prefix="email"),
            ]),
        ]

    # ── MEDIA MANAGER ────────────────────────────────────────────────────
    if role == MEDIA:
        return [
            NavItem("News & Media", "bi bi-newspaper", children=_media_items),
        ]

    # ── SCOUT ────────────────────────────────────────────────────────────
    if role == SCOUT:
        return [
            NavItem("Scouting", "bi bi-binoculars-fill", children=[
                NavItem("Dashboard",    "bi bi-binoculars","scout_dashboard"),
                NavItem("Browse Players","bi bi-people",  "scout_players"),
                NavItem("My Shortlist", "bi bi-star",     "scout_shortlist"),
            ]),
        ]

    # ── KICOSCA OFFICER ──────────────────────────────────────────────────
    if role == KICOSCA_OFFICER:
        return [
            NavItem("KICOSCA Games", "bi bi-trophy", children=[
                NavItem("My County",   "bi bi-speedometer2",             "kicosca_dashboard"),
                NavItem("Verification","bi bi-shield-check",             "kicosca_verification"),
                NavItem("Disciplines", "bi bi-trophy",                   "kicosca_add_discipline"),
            ]),
        ]

    # ── KICOSCA SG ───────────────────────────────────────────────────────
    if role == KICOSCA_SG:
        return [
            NavItem("KICOSCA Secretary General", "bi bi-shield-fill-check", children=[
                NavItem("Verification Dashboard","bi bi-shield-check","kicosca_verification"),
                NavItem("County View",           "bi bi-speedometer2","kicosca_dashboard"),
            ]),
        ]

    # Fallback — basic nav
    return []


# ---------------------------------------------------------------------------
# Bottom-nav (max 5 items — first item is always Dashboard/home for the role)
# ---------------------------------------------------------------------------

BOTTOM_NAV: dict[str, list[NavItem]] = {
    ADMIN: [
        NavItem("Home",    "bi bi-house-door",    "sys_admin_dashboard"),
        NavItem("Users",   "bi bi-people-fill",   "manage_users"),
        NavItem("Menu",    "bi bi-grid",           None),   # opens sidebar drawer
        NavItem("Logs",    "bi bi-journal-text",   "activity_logs"),
        NavItem("Profile", "bi bi-person-circle",  "web_profile"),
    ],
    CM: [
        NavItem("Home",     "bi bi-house-door",    "cm_dashboard"),
        NavItem("Comps",    "bi bi-trophy",        "competitions_list"),
        NavItem("Menu",     "bi bi-grid",           None),
        NavItem("Matches",  "bi bi-clipboard-data","matches_list"),
        NavItem("Profile",  "bi bi-person-circle", "web_profile"),
    ],
    SOCCER: [
        NavItem("Home",    "bi bi-house-door",    "coordinator_dashboard"),
        NavItem("Comps",   "bi bi-trophy",        "coordinator_competitions"),
        NavItem("Menu",    "bi bi-grid",           None),
        NavItem("Reports", "bi bi-clipboard-data","coordinator_match_reports"),
        NavItem("Profile", "bi bi-person-circle", "web_profile"),
    ],
    COUNTY_ADMIN: [
        NavItem("Home",    "bi bi-house-door",   "county_admin_dashboard"),
        NavItem("Players", "bi bi-people",       "county_admin_add_discipline"),
        NavItem("Menu",    "bi bi-grid",          None),
        NavItem("Payment", "bi bi-credit-card",  "county_admin_payment"),
        NavItem("Profile", "bi bi-person-circle","web_profile"),
    ],
    TREASURER: [
        NavItem("Home",    "bi bi-house-door",   "treasurer_dashboard"),
        NavItem("Payments","bi bi-building",     "treasurer_county_payments"),
        NavItem("Menu",    "bi bi-grid",          None),
        NavItem("Appeals", "bi bi-briefcase",    "appeals_list"),
        NavItem("Profile", "bi bi-person-circle","web_profile"),
    ],
    REFEREE: [
        NavItem("Home",    "bi bi-house-door",    "referee_portal"),
        NavItem("Squads",  "bi bi-clipboard-check","squad_review_list"),
        NavItem("Menu",    "bi bi-grid",           None),
        NavItem("Reports", "bi bi-file-earmark-text","matches_list"),
        NavItem("Profile", "bi bi-person-circle", "web_profile"),
    ],
    TEAM_MANAGER: [
        NavItem("Home",    "bi bi-house-door",   "team_manager_dashboard"),
        NavItem("Fixtures","bi bi-calendar-event","matches_list"),
        NavItem("Menu",    "bi bi-grid",          None),
        NavItem("Appeals", "bi bi-briefcase",    "appeals_list"),
        NavItem("Profile", "bi bi-person-circle","web_profile"),
    ],
    SCOUT: [
        NavItem("Home",     "bi bi-house-door",  "scout_dashboard"),
        NavItem("Players",  "bi bi-people",      "scout_players"),
        NavItem("Menu",     "bi bi-grid",         None),
        NavItem("Shortlist","bi bi-star",         "scout_shortlist"),
        NavItem("Profile",  "bi bi-person-circle","web_profile"),
    ],
}

# Default bottom nav for roles not explicitly listed above
_DEFAULT_BOTTOM_NAV = [
    NavItem("Home",    "bi bi-house-door",   "dashboard"),
    NavItem("Menu",    "bi bi-grid",          None),
    NavItem("Profile", "bi bi-person-circle","web_profile"),
]

# Reuse soccer coordinator bottom nav for all sport coordinators
for _r in (HANDBALL, BASKETBALL, VOLLEYBALL, COORDINATOR):
    BOTTOM_NAV[_r] = BOTTOM_NAV[SOCCER]


# ---------------------------------------------------------------------------
# Context processor
# ---------------------------------------------------------------------------

def portal_navigation(request):
    """
    Inject `portal_nav` and `portal_bottom_nav` into every template context.
    Both are lists of NavItem; templates use item.url_name, .icon, .label,
    .children, and item.is_active(url_name).

    Respects the role-preview session override set by RolePreviewMiddleware
    (request.user.role is already patched on the request object).
    """
    if not request.user.is_authenticated:
        return {}

    effective_role = getattr(request.user, "role", "")
    current_url   = getattr(getattr(request, "resolver_match", None), "url_name", "") or ""

    nav_sections   = _nav_for_role(effective_role)
    bottom_nav     = BOTTOM_NAV.get(effective_role, _DEFAULT_BOTTOM_NAV)

    return {
        "portal_nav":        nav_sections,
        "portal_bottom_nav": bottom_nav,
        "portal_role":       effective_role,
        "current_url_name":  current_url,
    }
