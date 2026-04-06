"""
KYISA Matches — Coordinator Event Management

Standalone CRUD for match events (goals, cards, etc.) by coordinators.
Allows editing/deleting individual events after match completion.

Endpoints:
  GET    /api/v1/matches/events/?fixture=<id>      — List events for a fixture
  POST   /api/v1/matches/events/                    — Add event
  PUT    /api/v1/matches/events/<id>/               — Edit event
  DELETE /api/v1/matches/events/<id>/               — Delete event
"""
import json
import logging

from rest_framework import status, permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from matches.models import MatchEvent, MatchReport
from matches.serializers import MatchEventSerializer
from accounts.permissions import IsCoordinatorOrAdmin

logger = logging.getLogger(__name__)


class MatchEventViewSet(ModelViewSet):
    """
    Full CRUD for match events.
    Coordinators can add, edit, and delete events post-match.
    All changes are logged to ActivityLog.
    """
    serializer_class = MatchEventSerializer
    permission_classes = [IsCoordinatorOrAdmin]
    filterset_fields = ["report__fixture", "team", "event_type"]

    def get_queryset(self):
        qs = MatchEvent.objects.select_related("player", "team", "report__fixture").all()
        # Allow filtering by fixture ID directly
        fixture_id = self.request.query_params.get("fixture")
        if fixture_id:
            qs = qs.filter(report__fixture_id=fixture_id)
        return qs

    @extend_schema(tags=["events"], summary="List match events")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["events"], summary="Add match event")
    def create(self, request, *args, **kwargs):
        # If fixture_id is provided instead of report, resolve it
        data = request.data.copy()
        if "fixture_id" in data and "report" not in data:
            try:
                report = MatchReport.objects.get(fixture_id=data["fixture_id"])
                data["report"] = report.id
            except MatchReport.DoesNotExist:
                return Response(
                    {"detail": "No match report found for this fixture."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        request._full_data = data  # noqa: SLF001
        response = super().create(request, *args, **kwargs)

        # Log the action
        self._log_event_action(
            request.user, "MATCH_UPDATE",
            f"Added event: {data.get('event_type')} at minute {data.get('minute')}",
            response.data.get("id"),
        )
        return response

    @extend_schema(tags=["events"], summary="Edit match event")
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        before_state = {
            "event_type": instance.event_type,
            "minute": instance.minute,
            "player_id": instance.player_id,
            "team_id": instance.team_id,
            "notes": instance.notes,
        }
        response = super().update(request, *args, **kwargs)

        self._log_event_action(
            request.user, "MATCH_UPDATE",
            f"Edited event {instance.id}: {before_state} → {request.data}",
            instance.id,
            before_state=before_state,
        )
        return response

    @extend_schema(tags=["events"], summary="Delete match event")
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        before_state = {
            "event_type": instance.event_type,
            "minute": instance.minute,
            "player_id": instance.player_id,
            "team_id": instance.team_id,
        }

        self._log_event_action(
            request.user, "MATCH_UPDATE",
            f"Deleted event: {instance.event_type} at minute {instance.minute}",
            instance.id,
            before_state=before_state,
        )
        return super().destroy(request, *args, **kwargs)

    def _log_event_action(self, user, action, description, event_id=None, before_state=None):
        """Log event changes to ActivityLog."""
        try:
            from admin_dashboard.models import ActivityLog
            ActivityLog.objects.create(
                user=user,
                action=action,
                description=description,
                previous_state=before_state,
            )
        except Exception as exc:
            logger.warning("Failed to log event action: %s", exc)
