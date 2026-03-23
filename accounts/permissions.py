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


class IsCoordinator(BasePermission):
    """Only a Discipline Coordinator can access."""
    message = "You must be a Discipline Coordinator to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.COORDINATOR)

IsRefereeManager = IsCoordinator  # backwards compat


class IsSportCoordinator(BasePermission):
    """Only a Sport Coordinator (Soccer, Handball, Basketball, Volleyball) can access."""
    message = "You must be a Sport Coordinator to perform this action."
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [
                UserRole.SOCCER_COORDINATOR,
                UserRole.HANDBALL_COORDINATOR,
                UserRole.BASKETBALL_COORDINATOR,
                UserRole.VOLLEYBALL_COORDINATOR,
            ]
        )


class IsSoccerCoordinator(BasePermission):
    """Only Soccer Coordinator can access."""
    message = "You must be a Soccer Coordinator to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.SOCCER_COORDINATOR)


class IsHandballCoordinator(BasePermission):
    """Only Handball Coordinator can access."""
    message = "You must be a Handball Coordinator to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.HANDBALL_COORDINATOR)


class IsBasketballCoordinator(BasePermission):
    """Only Basketball Coordinator can access."""
    message = "You must be a Basketball Coordinator to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.BASKETBALL_COORDINATOR)


class IsVolleyballCoordinator(BasePermission):
    """Only Volleyball Coordinator can access."""
    message = "You must be a Volleyball Coordinator to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.VOLLEYBALL_COORDINATOR)


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


class IsTreasurer(BasePermission):
    """Only the Treasurer can access."""
    message = "You must be a Treasurer to perform this action."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    request.user.role == UserRole.TREASURER)


class IsTreasurerOrAdmin(BasePermission):
    """Treasurer or Admin."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.is_staff or request.user.role in [
                UserRole.TREASURER, UserRole.ADMIN
            ])
        )


class IsAdminOrCompetitionManager(BasePermission):
    """Admin staff or Competition Manager."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.is_staff or request.user.role == UserRole.COMPETITION_MANAGER)
        )


class IsCoordinatorOrAdmin(BasePermission):
    """Discipline Coordinator or Admin."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.is_staff or request.user.role == UserRole.COORDINATOR)
        )

IsRefereeManagerOrAdmin = IsCoordinatorOrAdmin  # backwards compat


class IsAnyStaff(BasePermission):
    """Any internal staff role (CM, Coordinators, Treasurer, Admin) — not team manager or referee."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [
                UserRole.COMPETITION_MANAGER,
                UserRole.COORDINATOR,
                UserRole.SOCCER_COORDINATOR,
                UserRole.HANDBALL_COORDINATOR,
                UserRole.BASKETBALL_COORDINATOR,
                UserRole.VOLLEYBALL_COORDINATOR,
                UserRole.TREASURER,
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
            UserRole.COMPETITION_MANAGER, UserRole.COORDINATOR
        ]
