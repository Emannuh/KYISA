"""
Portal API views — JSON endpoints powering the React frontend.
Provides dashboard stats, clearance queue, treasurer data, admin overview,
and activity logs.
"""
from django.db.models import Count, Q, Avg
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers, status

from accounts.models import User
from teams.models import Team, Player
from competitions.models import Competition, Fixture, CountyPayment
from referees.models import RefereeProfile, RefereeAppointment
from appeals.models import Appeal
from admin_dashboard.models import ActivityLog


# ══════════════════════════════════════════════════════════════════════════════
#  SERIALIZERS (inline)
# ══════════════════════════════════════════════════════════════════════════════

class ClearanceRequestSerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Player
        fields = [
            'id', 'first_name', 'last_name', 'player_name',
            'team', 'team_name', 'national_id_number',
            'verification_status', 'huduma_status', 'fifa_connect_status',
            'status', 'registered_at',
        ]

    def get_player_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class PaymentSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='name', read_only=True)
    reference = serializers.CharField(source='payment_reference', read_only=True)
    amount = serializers.DecimalField(
        source='payment_amount', max_digits=12, decimal_places=2, read_only=True
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id', 'team_name', 'reference', 'amount', 'status',
            'payment_confirmed', 'payment_confirmed_at', 'registered_at',
        ]

    def get_status(self, obj):
        if obj.payment_confirmed:
            return 'verified'
        if obj.payment_reference:
            return 'pending'
        return 'unpaid'


class ActivityLogSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'user_display', 'action', 'description',
            'timestamp', 'object_repr', 'can_undo', 'is_undone',
        ]

    def get_user_display(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return '—'


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class PortalDashboardView(APIView):
    """Role-aware dashboard stats."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {}

        if user.is_admin or user.is_competition_manager:
            data.update({
                'total_teams': Team.objects.count(),
                'total_competitions': Competition.objects.count(),
                'pending_clearance': Player.objects.filter(verification_status='pending').count(),
                'active_appeals': Appeal.objects.exclude(status__in=['closed', 'decided']).count(),
                'pending_payments': Team.objects.filter(
                    payment_confirmed=False, payment_reference__gt=''
                ).count(),
            })

        if user.is_referee:
            profile = getattr(user, 'refereeprofile', None)
            if profile:
                data.update({
                    'upcoming_appointments': RefereeAppointment.objects.filter(
                        referee=profile,
                        status__in=['pending', 'confirmed'],
                        fixture__match_date__gte=timezone.now().date(),
                    ).count(),
                    'matches_officiated': profile.total_matches,
                    'avg_rating': float(profile.avg_rating) if profile.avg_rating else None,
                })

        if user.is_treasurer:
            data.update({
                'pending_payments': Team.objects.filter(
                    payment_confirmed=False, payment_reference__gt=''
                ).count(),
                'verified_payments': Team.objects.filter(payment_confirmed=True).count(),
                'total_revenue': str(
                    Team.objects.filter(payment_confirmed=True)
                    .exclude(payment_amount__isnull=True)
                    .aggregate(total=Count('payment_amount'))['total'] or 0
                ),
            })

        return Response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  CLEARANCE / VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class ClearanceListView(ListAPIView):
    """List players for verification/clearance queue."""
    permission_classes = [IsAuthenticated]
    serializer_class = ClearanceRequestSerializer

    def get_queryset(self):
        qs = Player.objects.select_related('team').order_by('-registered_at')
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if status_filter == 'pending':
            qs = qs.filter(verification_status='pending')
        elif status_filter == 'approved':
            qs = qs.filter(verification_status='verified')
        elif status_filter == 'rejected':
            qs = qs.filter(verification_status='rejected')

        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(national_id_number__icontains=search) |
                Q(team__name__icontains=search)
            )
        return qs


class ClearanceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            player = Player.objects.select_related('team').get(pk=pk)
        except Player.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        return Response(ClearanceRequestSerializer(player).data)


class ClearanceGrantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            player = Player.objects.get(pk=pk)
        except Player.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        player.verification_status = 'verified'
        player.verified_by = request.user
        player.verified_at = timezone.now()
        player.status = 'eligible'
        player.save()
        return Response({'detail': 'Player cleared'})


class ClearanceRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            player = Player.objects.get(pk=pk)
        except Player.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        player.verification_status = 'rejected'
        player.rejection_notes = request.data.get('reason', '')
        player.verified_by = request.user
        player.verified_at = timezone.now()
        player.save()
        return Response({'detail': 'Clearance rejected'})


# ══════════════════════════════════════════════════════════════════════════════
#  TREASURER
# ══════════════════════════════════════════════════════════════════════════════

class TreasurerPaymentsView(ListAPIView):
    """List teams with payment info for treasurer review."""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = Team.objects.order_by('-registered_at')
        status_filter = self.request.query_params.get('status')
        if status_filter == 'pending':
            qs = qs.filter(payment_confirmed=False, payment_reference__gt='')
        elif status_filter == 'verified':
            qs = qs.filter(payment_confirmed=True)
        elif status_filter == 'unpaid':
            qs = qs.filter(payment_reference='')
        return qs


class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        team.payment_confirmed = True
        team.payment_confirmed_by = request.user
        team.payment_confirmed_at = timezone.now()
        team.save()
        return Response({'detail': 'Payment verified'})


class PaymentRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        team.payment_confirmed = False
        team.payment_reference = ''
        team.save()
        return Response({'detail': 'Payment rejected'})


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN
# ══════════════════════════════════════════════════════════════════════════════

class AdminDashboardView(APIView):
    """Admin-level overview with big numbers."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'total_users': User.objects.count(),
            'total_teams': Team.objects.count(),
            'total_competitions': Competition.objects.count(),
            'total_referees': RefereeProfile.objects.count(),
            'pending_clearance': Player.objects.filter(verification_status='pending').count(),
            'pending_payments': Team.objects.filter(
                payment_confirmed=False, payment_reference__gt=''
            ).count(),
            'active_appeals': Appeal.objects.exclude(status__in=['closed', 'decided']).count(),
        })


class ActivityLogListView(ListAPIView):
    """Admin activity audit trail."""
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        return ActivityLog.objects.select_related('user').order_by('-timestamp')[:500]
