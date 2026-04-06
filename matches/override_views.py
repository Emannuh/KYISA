"""
KYISA — Result Override API

Allows coordinators to override a completed fixture's score
with safeguards: confirmation checkbox, minimum 12-char reason,
before/after audit trail, and automatic standings recalculation.
"""
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction

from accounts.permissions import IsCoordinatorOrAdmin
from competitions.models import Fixture, FixtureStatus, PoolTeam
from admin_dashboard.models import ActivityLog


class ResultOverrideSerializer(serializers.Serializer):
    home_score = serializers.IntegerField(min_value=0)
    away_score = serializers.IntegerField(min_value=0)
    confirm_exceptional = serializers.BooleanField()
    override_reason = serializers.CharField(min_length=12)

    def validate_confirm_exceptional(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must confirm this is an exceptional circumstance."
            )
        return value


class ResultOverrideView(APIView):
    """POST /api/v1/matches/fixtures/<pk>/override-result/"""

    permission_classes = [IsCoordinatorOrAdmin]

    def post(self, request, pk):
        fixture = get_object_or_404(Fixture, pk=pk, status=FixtureStatus.COMPLETED)

        ser = ResultOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        before = {
            "home_score": fixture.home_score,
            "away_score": fixture.away_score,
        }

        with transaction.atomic():
            fixture.home_score = ser.validated_data["home_score"]
            fixture.away_score = ser.validated_data["away_score"]
            fixture.save(update_fields=["home_score", "away_score"])

            after = {
                "home_score": fixture.home_score,
                "away_score": fixture.away_score,
            }

            ActivityLog.objects.create(
                action="RESULT_OVERRIDE",
                user=request.user,
                description=(
                    f"Result override for {fixture}: "
                    f"{before['home_score']}-{before['away_score']} → "
                    f"{after['home_score']}-{after['away_score']}. "
                    f"Reason: {ser.validated_data['override_reason']}"
                ),
                previous_state=before,
                new_state=after,
                can_undo=True,
            )

            # Recalculate pool standings if fixture belongs to a pool
            if fixture.pool:
                from matches.stats_engine import recalculate_pool_standings
                recalculate_pool_standings(fixture.pool)

        # Send notification
        try:
            from kyisa_cms.notifications import notify_result_override
            notify_result_override(fixture, before, after, ser.validated_data["override_reason"])
        except Exception:
            pass

        return Response({
            "detail": "Result overridden successfully.",
            "before": before,
            "after": after,
        })
