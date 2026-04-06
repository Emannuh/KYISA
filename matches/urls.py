from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SquadSubmitView, SquadListView, SquadApproveView,
    MatchReportViewSet, MatchReportApproveView,
)
from .live_views import (
    LiveStartView, LiveGoalView, LiveEventView,
    LivePauseView, LiveResumeView, LivePeriodView,
    LiveEndView, LiveScoreboardView,
)
from .event_views import MatchEventViewSet
from .override_views import ResultOverrideView

router = DefaultRouter()
router.register(r"reports", MatchReportViewSet, basename="match-report")
router.register(r"events", MatchEventViewSet, basename="match-event")

urlpatterns = [
    # Squad
    path("squads/",                  SquadSubmitView.as_view(),    name="squad-submit"),
    path("squads/list/",             SquadListView.as_view(),      name="squad-list"),
    path("squads/<int:pk>/approve/", SquadApproveView.as_view(),   name="squad-approve"),
    # Reports
    path("reports/<int:pk>/approve/",MatchReportApproveView.as_view(), name="report-approve"),
    # Live match tracking
    path("live/<int:fixture_id>/start/",      LiveStartView.as_view(),      name="live-start"),
    path("live/<int:fixture_id>/goal/",       LiveGoalView.as_view(),       name="live-goal"),
    path("live/<int:fixture_id>/event/",      LiveEventView.as_view(),      name="live-event"),
    path("live/<int:fixture_id>/pause/",      LivePauseView.as_view(),      name="live-pause"),
    path("live/<int:fixture_id>/resume/",     LiveResumeView.as_view(),     name="live-resume"),
    path("live/<int:fixture_id>/period/",     LivePeriodView.as_view(),     name="live-period"),
    path("live/<int:fixture_id>/end/",        LiveEndView.as_view(),        name="live-end"),
    path("live/<int:fixture_id>/scoreboard/", LiveScoreboardView.as_view(), name="live-scoreboard"),
    # Result override
    path("fixtures/<int:pk>/override-result/", ResultOverrideView.as_view(), name="result-override"),
    path("", include(router.urls)),
]
