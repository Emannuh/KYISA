"""
KYISA CMS — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from .web_views import (
    # Public website
    home_view, about_view, public_competitions_view,
    public_competition_detail_view, public_results_view,
    public_statistics_view, public_competition_standings_view,
    contact_view,
    # Public registration
    team_register_view, team_register_success_view,
    referee_register_view, referee_register_success_view,
    # CMS portal
    web_login_view, web_logout_view, dashboard_view,
    force_change_password_view,
    competitions_list_view, competition_detail_view,
    teams_list_view, team_detail_view,
    referees_list_view,
    matches_list_view,
    profile_view, change_password_view,
    # Player management
    add_player_view, edit_player_view, delete_player_view,
    # Admin approval
    pending_teams_view, pending_referees_view,
    # Player verification
    player_verification_list_view, verify_player_view,
    # Squad selection & approval
    squad_select_view, squad_review_list_view, squad_review_view,
    # Match reporting
    match_report_form_view, match_report_detail_view, match_report_review_view,
    # Referee appointments & portal
    appointment_action_view,
    referee_dashboard_view, referee_availability_view,
    # Referee manager — appointment management
    referee_appointments_view, referee_appoint_view,
    # Treasurer portal
    treasurer_dashboard_view,
    treasurer_teams_view,
    treasurer_county_payments_view,
    # Competition Manager specific views
    competition_standings_view,
    competition_reports_view,
    competition_report_approve_view,
    # Competition Manager — full portal
    cm_dashboard_view,
    cm_create_competition_view,
    cm_edit_competition_view,
    cm_competition_manage_view,
    cm_manage_pools_view,
    cm_generate_fixtures_view,
    cm_manage_venues_view,
    cm_allocate_venue_view,
    cm_edit_standings_view,
    cm_edit_fixture_view,
    cm_competition_rules_view,
)

urlpatterns = [
    # ── PUBLIC WEBSITE ────────────────────────────────────────────────────────
    path("",                              home_view,                      name="home"),
    path("about/",                        about_view,                     name="about"),
    path("competitions/public/",          public_competitions_view,       name="public_competitions"),
    path("competitions/public/<int:pk>/", public_competition_detail_view, name="public_competition_detail"),
    path("results/",                      public_results_view,            name="public_results"),
    path("results/statistics/",            public_statistics_view,         name="public_statistics"),
    path("results/competitions/<int:pk>/standings/", public_competition_standings_view, name="public_competition_standings"),
    path("contact/",                      contact_view,                   name="contact"),

    # ── PUBLIC REGISTRATION ───────────────────────────────────────────────────
    path("register/team/",            team_register_view,          name="team_register"),
    path("register/team/success/",    team_register_success_view,  name="team_register_success"),
    path("register/referee/",         referee_register_view,       name="referee_register"),
    path("register/referee/success/", referee_register_success_view, name="referee_register_success"),

    # ── CMS PORTAL (Authenticated) ───────────────────────────────────────────
    path("portal/login/",                   web_login_view,         name="web_login"),
    path("portal/logout/",                  web_logout_view,        name="web_logout"),
    path("portal/force-change-password/",   force_change_password_view, name="force_change_password"),
    path("portal/",                         dashboard_view,         name="dashboard"),
    path("portal/competitions/",            competitions_list_view, name="competitions_list"),
    path("portal/competitions/<int:pk>/",   competition_detail_view, name="competition_detail"),
    path("portal/teams/",                   teams_list_view,        name="teams_list"),
    path("portal/teams/<int:pk>/",          team_detail_view,       name="team_detail"),
    path("portal/teams/<int:team_pk>/add-player/", add_player_view,  name="add_player"),
    path("portal/players/<int:player_pk>/edit/",    edit_player_view, name="edit_player"),
    path("portal/players/<int:player_pk>/delete/",  delete_player_view, name="delete_player"),
    path("portal/referees/",                referees_list_view,     name="referees_list"),
    path("portal/matches/",                 matches_list_view,      name="matches_list"),
    path("portal/profile/",                 profile_view,           name="web_profile"),
    path("portal/profile/change-password/", change_password_view,  name="web_change_password"),

    # ── PORTAL: APPROVAL WORKFLOWS ───────────────────────────────────────────
    path("portal/teams/pending/",    pending_teams_view,    name="pending_teams"),
    path("portal/referees/pending/", pending_referees_view, name="pending_referees"),
    # ── PORTAL: PLAYER VERIFICATION ─────────────────────────────────────
    path("portal/players/verification/",              player_verification_list_view, name="player_verification_list"),
    path("portal/players/<int:player_pk>/verify/",    verify_player_view,            name="verify_player"),

    # ── PORTAL: SQUAD SELECTION & APPROVAL ────────────────────────────────
    path("portal/fixtures/<int:fixture_pk>/squad/",       squad_select_view,      name="squad_select"),
    path("portal/squads/review/",                         squad_review_list_view,  name="squad_review_list"),
    path("portal/squads/<int:squad_pk>/review/",          squad_review_view,       name="squad_review"),

    # ── PORTAL: MATCH REPORTS ─────────────────────────────────────────────
    path("portal/fixtures/<int:fixture_pk>/report/",      match_report_form_view,    name="match_report_form"),
    path("portal/reports/<int:report_pk>/",               match_report_detail_view,  name="match_report_detail"),
    path("portal/reports/<int:report_pk>/review/",        match_report_review_view,  name="match_report_review"),

    # ── PORTAL: REFEREE APPOINTMENTS ──────────────────────────────────────
    path("portal/appointments/<int:appointment_pk>/",     appointment_action_view,    name="appointment_action"),

    # ── PORTAL: REFEREE MANAGER — APPOINTMENT MANAGEMENT ──────────────────
    path("portal/referee-manager/appointments/",                   referee_appointments_view, name="referee_appointments"),
    path("portal/referee-manager/appointments/<int:fixture_pk>/",  referee_appoint_view,      name="referee_appoint"),

    # ── PORTAL: REFEREE DASHBOARD & AVAILABILITY ──────────────────────────
    path("portal/referee/",                               referee_dashboard_view,     name="referee_portal"),
    path("portal/referee/availability/",                  referee_availability_view,  name="referee_availability"),

    # ── TREASURER PORTAL ────────────────────────────────────────────────────
    path("portal/treasurer/",                treasurer_dashboard_view,       name="treasurer_dashboard"),
    path("portal/treasurer/teams/",          treasurer_teams_view,           name="treasurer_teams"),
    path("portal/treasurer/county-payments/", treasurer_county_payments_view, name="treasurer_county_payments"),

    # ── COMPETITION MANAGER PORTAL ────────────────────────────────────────
    path("portal/competitions/<int:pk>/standings/",   competition_standings_view,      name="competition_standings"),
    path("portal/competitions/<int:pk>/reports/",     competition_reports_view,        name="competition_reports"),
    path("portal/competitions/<int:pk>/reports/<int:report_pk>/approve/",
         competition_report_approve_view, name="competition_report_approve"),

    # ── COMPETITION MANAGER — FULL MANAGEMENT ─────────────────────────────
    path("portal/cm/",                                     cm_dashboard_view,             name="cm_dashboard"),
    path("portal/cm/create/",                              cm_create_competition_view,    name="cm_create_competition"),
    path("portal/cm/competitions/<int:pk>/edit/",          cm_edit_competition_view,      name="cm_edit_competition"),
    path("portal/cm/competitions/<int:pk>/",               cm_competition_manage_view,    name="cm_competition_manage"),
    path("portal/cm/competitions/<int:pk>/pools/",         cm_manage_pools_view,          name="cm_manage_pools"),
    path("portal/cm/competitions/<int:pk>/fixtures/generate/", cm_generate_fixtures_view, name="cm_generate_fixtures"),
    path("portal/cm/competitions/<int:pk>/venues/",        cm_allocate_venue_view,        name="cm_allocate_venues"),
    path("portal/cm/competitions/<int:pk>/standings/edit/", cm_edit_standings_view,       name="cm_edit_standings"),
    path("portal/cm/competitions/<int:pk>/fixtures/<int:fixture_pk>/edit/",
         cm_edit_fixture_view, name="cm_edit_fixture"),
    path("portal/cm/competitions/<int:pk>/rules/",         cm_competition_rules_view,     name="cm_competition_rules"),
    path("portal/cm/venues/",                              cm_manage_venues_view,         name="cm_venues"),

    # ── ADMIN DASHBOARD ───────────────────────────────────────────────────────
    path("portal/admin-dashboard/", include("admin_dashboard.urls")),

    # ── APPEALS & JURY ────────────────────────────────────────────────────────
    path("portal/appeals/", include("appeals.urls")),

    # ── DJANGO ADMIN ─────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── API v1 ────────────────────────────────────────────────────────────────
    path("api/v1/auth/",         include("accounts.urls")),
    path("api/v1/competitions/", include("competitions.urls")),
    path("api/v1/referees/",     include("referees.urls")),
    path("api/v1/teams/",        include("teams.urls")),
    path("api/v1/matches/",      include("matches.urls")),

    # ── API DOCUMENTATION ─────────────────────────────────────────────────────
    path("api/schema/", SpectacularAPIView.as_view(),                        name="schema"),
    path("api/docs/",   SpectacularSwaggerView.as_view(url_name="schema"),   name="swagger-ui"),
    path("api/redoc/",  SpectacularRedocView.as_view(url_name="schema"),     name="redoc"),
]

# ── SERVE MEDIA IN DEVELOPMENT ────────────────────────────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ── ADMIN CUSTOMISATION ───────────────────────────────────────────────────────
admin.site.site_header = "KYISA Competition Management System"
admin.site.site_title  = "KYISA Admin"
admin.site.index_title = "Administration Dashboard"