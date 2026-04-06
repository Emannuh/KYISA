from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeamViewSet, PlayerViewSet
from .bulk_upload import BulkPlayerUploadView, BulkPlayerTemplateView

router = DefaultRouter()
router.register(r"",        TeamViewSet,  basename="team")
router.register(r"players", PlayerViewSet, basename="player")

urlpatterns = [
    path("players/bulk-upload/",  BulkPlayerUploadView.as_view(),  name="player-bulk-upload"),
    path("players/bulk-template/", BulkPlayerTemplateView.as_view(), name="player-bulk-template"),
    path("", include(router.urls)),
]
