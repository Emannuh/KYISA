from django.urls import path
from . import views

urlpatterns = [
    # County director portal
    path('',                                          views.kicosca_dashboard,           name='kicosca_dashboard'),
    path('join/',                                     views.kicosca_join,                name='kicosca_join'),
    path('add-discipline/',                           views.kicosca_add_discipline,      name='kicosca_add_discipline'),
    path('discipline/<int:discipline_pk>/',           views.kicosca_discipline_players,  name='kicosca_discipline_players'),
    path('discipline/<int:discipline_pk>/add-player/', views.kicosca_add_player,         name='kicosca_add_player'),
    path('player/<int:player_pk>/',                   views.kicosca_player_detail,       name='kicosca_player_detail'),
    path('player/<int:player_pk>/delete/',            views.kicosca_delete_player,       name='kicosca_delete_player'),
    path('player/<int:player_pk>/kra-verify/',        views.kicosca_kra_verify,          name='kicosca_kra_verify'),

    # Admin verification dashboard
    path('verification/',                             views.kicosca_verification_dashboard, name='kicosca_verification'),

    # AJAX endpoints
    path('api/iprs-lookup/',                          views.kicosca_iprs_lookup,         name='kicosca_iprs_lookup'),
    path('api/kra-pin-lookup/',                       views.kicosca_kra_pin_lookup,      name='kicosca_kra_pin_lookup'),
]
