"""
KYISA — Role-Based Permission Classes
"""
from rest_framework.permissions import BasePermission
from accounts.models import UserRole


class IsCompetitionManager(BasePermission):
    """Only the Competition Manager can access."""
    message = "You must be a Competition Manager to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.COMPETITION_MANAGER)


class IsRefereeManager(BasePermission):
    """Only the Referee Manager can access."""
    message = "You must be a Referee Manager to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.REFEREE_MANAGER)


class IsReferee(BasePermission):
    """Only approved Referees can access."""
    message = "You must be an approved Referee to perform this action."
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role != UserRole.REFEREE:
            return False
        # Must have a referee profile and be approved
        try:
            return request.user.referee_profile.is_approved
        except Exception:
            return False


class IsTeamManager(BasePermission):
    """Only Team Managers can access."""
    message = "You must be a Team Manager to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.TEAM_MANAGER)


class IsAdminOrCompetitionManager(BasePermission):
    """Admin staff or Competition Manager."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.is_staff or request.user.role == UserRole.COMPETITION_MANAGER)
        )


class IsRefereeManagerOrAdmin(BasePermission):
    """Referee Manager or Admin."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.is_staff or request.user.role == UserRole.REFEREE_MANAGER)
        )


class IsAnyStaff(BasePermission):
    """Any internal staff role (CM, RM, Admin) — not team manager or referee."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [
                UserRole.COMPETITION_MANAGER,
                UserRole.REFEREE_MANAGER,
                UserRole.ADMIN,
            ]
        )


class ReadOnly(BasePermission):
    """Authenticated users can read; only admins/managers can write."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.is_staff or request.user.role in [
            UserRole.COMPETITION_MANAGER, UserRole.REFEREE_MANAGER
        ]
