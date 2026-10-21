"""
KYISA Accounts — Force Password Change Middleware

Redirects any authenticated user with `must_change_password=True`
to the password-change page.  The only pages they are allowed to
visit are the change-password page, logout, and static/media files.
"""
from django.shortcuts import redirect
from django.urls import reverse


# URL names the user may still visit while forced to change password
ALLOWED_URL_NAMES = {
    "force_change_password",
    "web_logout",
    "web_login",
}

# Prefixes that should never be blocked (static assets, API, admin)
ALLOWED_PATH_PREFIXES = (
    "/static/",
    "/media/",
    "/admin/",
    "/api/",
)

# Exact paths that must always be accessible during forced password change
ALLOWED_PATHS = {
    "/portal/force-change-password/",
    "/portal/logout/",
    "/portal/login/",
}


class ForcePasswordChangeMiddleware:
    """
    If request.user.must_change_password is True, redirect every page
    request to the force-change-password page until they set a new password.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, "must_change_password", False):
            # Allow the whitelisted path prefixes through
            if request.path.startswith(ALLOWED_PATH_PREFIXES):
                return self.get_response(request)

            # Allow exact whitelisted paths through
            if request.path in ALLOWED_PATHS:
                return self.get_response(request)

            # Allow whitelisted URL names through (fallback)
            current_url_name = getattr(request.resolver_match, "url_name", None)
            if current_url_name in ALLOWED_URL_NAMES:
                return self.get_response(request)

            return redirect("force_change_password")

        return self.get_response(request)


# ── Valid roles that can be previewed ────────────────────────────────────────
PREVIEWABLE_ROLES = {
    'competition_manager',
    'coordinator',
    'soccer_coordinator',
    'handball_coordinator',
    'basketball_coordinator',
    'volleyball_coordinator',
    'verification_officer',
    'referee',
    'team_manager',
    'county_sports_admin',
    'treasurer',
    'secretary_general',
    'scout',
    'media_manager',
    'jury_chair',
    'cec_sports',
}

PREVIEW_SESSION_KEY = '_preview_role'


class RolePreviewMiddleware:
    """
    Allows system admins (is_superuser or role='admin') to preview the portal
    as any other role — useful for demos and debugging.

    Usage:
      - Start preview:  GET /portal/preview-role/referee/
      - Stop preview:   GET /portal/preview-role/exit/

    While in preview mode:
      - request.user.role is temporarily patched to the preview role
      - A banner is injected into the response (via context processor or base template tag)
      - All role_required decorators pass because they check request.user.role
      - The actual DB role is never changed
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and (request.user.is_superuser or getattr(request.user, 'role', '') == 'admin')
        ):
            preview_role = request.session.get(PREVIEW_SESSION_KEY)
            if preview_role and preview_role in PREVIEWABLE_ROLES:
                # Patch role for this request only — does NOT touch the DB
                request.user._real_role = request.user.role
                request.user.role       = preview_role
                request._role_preview   = preview_role
            else:
                request._role_preview = None
        else:
            request._role_preview = None

        return self.get_response(request)
