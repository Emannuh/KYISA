"""
KYISA Matches — Live Match Tracking API Endpoints

Seven endpoints for real-time match state management:
  POST /api/v1/matches/live/<fixture_id>/start/
  POST /api/v1/matches/live/<fixture_id>/goal/
  POST /api/v1/matches/live/<fixture_id>/event/
  POST /api/v1/matches/live/<fixture_id>/pause/
  POST /api/v1/matches/live/<fixture_id>/resume/
  POST /api/v1/matches/live/<fixture_id>/period/
  POST /api/v1/matches/live/<fixture_id>/end/
"""
from rest_framework import serializers, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from competitions.models import Fixture, FixtureStatus
from matches.models import MatchReport, MatchEvent, get_sport_config
from accounts.permissions import IsCoordinatorOrAdmin, IsAnyStaff


class IsLiveUpdater(permissions.BasePermission):
    """Coordinator, Admin, or assigned Referee can update live matches."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        from accounts.models import UserRole
        return request.user.role in [
            UserRole.COORDINATOR,
            UserRole.SOCCER_COORDINATOR,
            UserRole.HANDBALL_COORDINATOR,
            UserRole.BASKETBALL_COORDINATOR,
            UserRole.VOLLEYBALL_COORDINATOR,
            UserRole.COMPETITION_MANAGER,
            UserRole.REFEREE,
            UserRole.ADMIN,
        ] or request.user.is_staff


def _fixture_data(fixture):
    """Return serialized fixture state for live responses."""
    return {
        "id": fixture.id,
        "status": fixture.status,
        "home_team": fixture.home_team.name,
        "away_team": fixture.away_team.name,
        "home_score": fixture.home_score,
        "away_score": fixture.away_score,
        "live_half": fixture.live_half,
        "live_paused": fixture.live_paused,
        "live_paused_minute": fixture.live_paused_minute,
        "live_extra_minutes": fixture.live_extra_minutes,
        "live_started_at": fixture.live_started_at.isoformat() if fixture.live_started_at else None,
    }


class LiveStartView(APIView):
    """POST /api/v1/matches/live/<fixture_id>/start/ — Start a match."""
    permission_classes = [IsLiveUpdater]

    @extend_schema(tags=["live"], summary="Start a match (kick-off)")
    def post(self, request, fixture_id):
        fixture = get_object_or_404(Fixture, pk=fixture_id)
        if fixture.status not in (FixtureStatus.PENDING, FixtureStatus.CONFIRMED):
            return Response(
                {"detail": f"Cannot start match in '{fixture.status}' state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        fixture.status = FixtureStatus.LIVE
        fixture.live_started_at = request.data.get("started_at", now)
        fixture.live_half = 1
        fixture.live_paused = False
        fixture.live_extra_minutes = 0
        fixture.home_score = fixture.home_score or 0
        fixture.away_score = fixture.away_score or 0
        fixture.save(update_fields=[
            "status", "live_started_at", "live_half", "live_paused",
            "live_extra_minutes", "home_score", "away_score",
        ])

        return Response({"detail": "Match started.", "fixture": _fixture_data(fixture)})


class LiveGoalView(APIView):
    """POST /api/v1/matches/live/<fixture_id>/goal/ — Record a goal."""
    permission_classes = [IsLiveUpdater]

    @extend_schema(tags=["live"], summary="Record a goal during live match")
    def post(self, request, fixture_id):
        fixture = get_object_or_404(Fixture, pk=fixture_id, status=FixtureStatus.LIVE)
        team_id = request.data.get("team_id")
        player_id = request.data.get("player_id")
        minute = request.data.get("minute", 0)
        is_penalty = request.data.get("is_penalty", False)
        assist_player_id = request.data.get("assist_player_id")
        notes = request.data.get("notes", "")

        if not team_id:
            return Response({"detail": "team_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Update score
        if int(team_id) == fixture.home_team_id:
            fixture.home_score = (fixture.home_score or 0) + 1
        elif int(team_id) == fixture.away_team_id:
            fixture.away_score = (fixture.away_score or 0) + 1
        else:
            return Response({"detail": "team_id must be home or away team."}, status=status.HTTP_400_BAD_REQUEST)
        fixture.save(update_fields=["home_score", "away_score"])

        # Create match event (linked to report if exists, or standalone)
        report = MatchReport.objects.filter(fixture=fixture).first()
        if report:
            event_type = "penalty" if is_penalty else "goal"
            MatchEvent.objects.create(
                report=report, team_id=team_id, player_id=player_id,
                event_type=event_type, minute=minute, notes=notes,
            )
            # Create assist event if provided
            if assist_player_id:
                MatchEvent.objects.create(
                    report=report, team_id=team_id, player_id=assist_player_id,
                    event_type="assist", minute=minute, notes=f"Assist for goal",
                )

        return Response({
            "detail": "Goal recorded.",
            "fixture": _fixture_data(fixture),
        })


class LiveEventView(APIView):
    """POST /api/v1/matches/live/<fixture_id>/event/ — Record a match event."""
    permission_classes = [IsLiveUpdater]

    @extend_schema(tags=["live"], summary="Record match event (card, sub, injury, etc.)")
    def post(self, request, fixture_id):
        fixture = get_object_or_404(Fixture, pk=fixture_id, status=FixtureStatus.LIVE)
        event_type = request.data.get("event_type")
        team_id = request.data.get("team_id")
        player_id = request.data.get("player_id")
        minute = request.data.get("minute", 0)
        notes = request.data.get("notes", "")

        if not event_type or not team_id:
            return Response(
                {"detail": "event_type and team_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate event_type against sport config
        valid_types = [et[0] for et in MatchEvent.EVENT_TYPES]
        if event_type not in valid_types:
            return Response(
                {"detail": f"Invalid event_type '{event_type}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = MatchReport.objects.filter(fixture=fixture).first()
        event_data = {
            "team_id": team_id,
            "player_id": player_id,
            "event_type": event_type,
            "minute": minute,
            "notes": notes,
        }
        event = None
        if report:
            event = MatchEvent.objects.create(report=report, **event_data)

        return Response({
            "detail": f"Event '{event_type}' recorded.",
            "event": {"id": event.id, **event_data} if event else event_data,
            "fixture": _fixture_data(fixture),
        })


class LivePauseView(APIView):
    """POST /api/v1/matches/live/<fixture_id>/pause/ — Pause match clock."""
    permission_classes = [IsLiveUpdater]

    @extend_schema(tags=["live"], summary="Pause match clock")
    def post(self, request, fixture_id):
        fixture = get_object_or_404(Fixture, pk=fixture_id, status=FixtureStatus.LIVE)
        paused_minute = request.data.get("paused_minute")

        fixture.live_paused = True
        if paused_minute is not None:
            fixture.live_paused_minute = int(paused_minute)
        fixture.save(update_fields=["live_paused", "live_paused_minute"])

        return Response({"detail": "Match paused.", "fixture": _fixture_data(fixture)})


class LiveResumeView(APIView):
    """POST /api/v1/matches/live/<fixture_id>/resume/ — Resume match clock."""
    permission_classes = [IsLiveUpdater]

    @extend_schema(tags=["live"], summary="Resume match clock")
    def post(self, request, fixture_id):
        fixture = get_object_or_404(Fixture, pk=fixture_id, status=FixtureStatus.LIVE)

        fixture.live_paused = False
        fixture.save(update_fields=["live_paused"])

        return Response({"detail": "Match resumed.", "fixture": _fixture_data(fixture)})


class LivePeriodView(APIView):
    """POST /api/v1/matches/live/<fixture_id>/period/ — Change period/half."""
    permission_classes = [IsLiveUpdater]

    @extend_schema(tags=["live"], summary="Change match period (half-time, etc.)")
    def post(self, request, fixture_id):
        fixture = get_object_or_404(Fixture, pk=fixture_id, status=FixtureStatus.LIVE)
        new_half = request.data.get("live_half")
        extra_minutes = request.data.get("extra_minutes", 0)

        if new_half is None:
            return Response(
                {"detail": "live_half is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fixture.live_half = int(new_half)
        fixture.live_extra_minutes = int(extra_minutes)
        fixture.live_paused = False
        fixture.live_paused_minute = None
        fixture.save(update_fields=[
            "live_half", "live_extra_minutes", "live_paused", "live_paused_minute",
        ])

        return Response({"detail": f"Period changed to {new_half}.", "fixture": _fixture_data(fixture)})


class LiveEndView(APIView):
    """POST /api/v1/matches/live/<fixture_id>/end/ — End match."""
    permission_classes = [IsLiveUpdater]

    @extend_schema(tags=["live"], summary="End match (full time)")
    def post(self, request, fixture_id):
        fixture = get_object_or_404(Fixture, pk=fixture_id, status=FixtureStatus.LIVE)
        final_home = request.data.get("final_home_score")
        final_away = request.data.get("final_away_score")

        if final_home is not None:
            fixture.home_score = int(final_home)
        if final_away is not None:
            fixture.away_score = int(final_away)

        fixture.status = FixtureStatus.COMPLETED
        fixture.live_paused = False
        fixture.live_paused_minute = None
        fixture.determine_winner()
        fixture.save()

        return Response({
            "detail": "Match ended.",
            "fixture": _fixture_data(fixture),
        })


class LiveScoreboardView(APIView):
    """GET /api/v1/matches/live/<fixture_id>/scoreboard/ — Public live scoreboard data."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(tags=["live"], summary="Get live scoreboard data (public)")
    def get(self, request, fixture_id):
        fixture = get_object_or_404(
            Fixture.objects.select_related(
                "home_team", "away_team", "venue", "competition"
            ),
            pk=fixture_id,
        )

        # Get recent events
        events = []
        report = MatchReport.objects.filter(fixture=fixture).first()
        if report:
            recent = report.events.select_related("player", "team").order_by("-minute")[:20]
            events = [
                {
                    "event_type": e.event_type,
                    "minute": e.minute,
                    "player": e.player.get_full_name() if e.player else None,
                    "team": e.team.name,
                    "notes": e.notes,
                }
                for e in recent
            ]

        # Get squads (starters only for public)
        from matches.models import SquadSubmission
        home_squad = []
        away_squad = []
        for sq in SquadSubmission.objects.filter(fixture=fixture, status="approved").prefetch_related("squad_players__player"):
            players = [
                {
                    "name": sp.player.get_full_name(),
                    "shirt_number": sp.shirt_number,
                    "is_starter": sp.is_starter,
                    "position": sp.player.get_position_display() if hasattr(sp.player, "get_position_display") else sp.player.position,
                }
                for sp in sq.squad_players.all()
            ]
            if sq.team_id == fixture.home_team_id:
                home_squad = players
            else:
                away_squad = players

        return Response({
            "fixture": _fixture_data(fixture),
            "competition": fixture.competition.name if fixture.competition else None,
            "venue": fixture.venue.name if fixture.venue else None,
            "match_date": fixture.match_date.isoformat(),
            "kickoff_time": fixture.kickoff_time.isoformat() if fixture.kickoff_time else None,
            "events": events,
            "home_squad": home_squad,
            "away_squad": away_squad,
        })
