from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeamViewSet, PlayerViewSet
from .bulk_upload import (
    BulkPlayerUploadView,
    BulkPlayerTemplateView,
    CountyBulkPlayerUploadView,
    CountyBulkPlayerTemplateView,
)

router = DefaultRouter()
router.register(r"",        TeamViewSet,  basename="team")
router.register(r"players", PlayerViewSet, basename="player")

urlpatterns = [
    path("players/bulk-upload/",  BulkPlayerUploadView.as_view(),  name="player-bulk-upload"),
    path("players/bulk-template/", BulkPlayerTemplateView.as_view(), name="player-bulk-template"),
    path("county-players/bulk-upload/", CountyBulkPlayerUploadView.as_view(), name="county-player-bulk-upload"),
    path("county-players/bulk-template/", CountyBulkPlayerTemplateView.as_view(), name="county-player-bulk-template"),
    path("", include(router.urls)),
]
