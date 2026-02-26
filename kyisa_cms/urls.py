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
    public_competition_detail_view, public_results_view, contact_view,
    # CMS portal
    web_login_view, web_logout_view, dashboard_view,
    competitions_list_view, competition_detail_view,
    teams_list_view, team_detail_view,
    referees_list_view,
    matches_list_view,
    profile_view, change_password_view,
)

urlpatterns = [
    # ── PUBLIC WEBSITE ────────────────────────────────────────────────────────
    path("",                              home_view,                          name="home"),
    path("about/",                        about_view,                         name="about"),
    path("competitions/public/",          public_competitions_view,           name="public_competitions"),
    path("competitions/public/<int:pk>/", public_competition_detail_view,     name="public_competition_detail"),
    path("results/",                      public_results_view,                name="public_results"),
    path("contact/",                      contact_view,                       name="contact"),

    # ── CMS PORTAL (Authenticated) ───────────────────────────────────────────
    path("portal/login/",                web_login_view,            name="web_login"),
    path("portal/logout/",               web_logout_view,           name="web_logout"),
    path("portal/",                      dashboard_view,            name="dashboard"),
    path("portal/competitions/",         competitions_list_view,    name="competitions_list"),
    path("portal/competitions/<int:pk>/",competition_detail_view,   name="competition_detail"),
    path("portal/teams/",               teams_list_view,           name="teams_list"),
    path("portal/teams/<int:pk>/",       team_detail_view,          name="team_detail"),
    path("portal/referees/",             referees_list_view,        name="referees_list"),
    path("portal/matches/",              matches_list_view,         name="matches_list"),
    path("portal/profile/",              profile_view,              name="web_profile"),
    path("portal/profile/change-password/", change_password_view,   name="web_change_password"),

    # ── ADMIN ─────────────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── API v1 ────────────────────────────────────────────────────────────────
    path("api/v1/auth/",         include("accounts.urls")),
    path("api/v1/competitions/", include("competitions.urls")),
    path("api/v1/referees/",     include("referees.urls")),
    path("api/v1/teams/",        include("teams.urls")),
    path("api/v1/matches/",      include("matches.urls")),

    # ── API DOCUMENTATION ─────────────────────────────────────────────────────
    path("api/schema/",         SpectacularAPIView.as_view(),          name="schema"),
    path("api/docs/",           SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/",          SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),
]

# ── SERVE MEDIA IN DEVELOPMENT ────────────────────────────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ── ADMIN CUSTOMISATION ───────────────────────────────────────────────────────
admin.site.site_header  = "KYISA Competition Management System"
admin.site.site_title   = "KYISA Admin"
admin.site.index_title  = "Administration Dashboard"
