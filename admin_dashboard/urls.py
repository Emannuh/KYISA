# admin_dashboard/urls.py
from django.urls import path

from . import views

from . import admin_views
from . import reschedule_admin_views
from . import activity_views


urlpatterns = [
    # Admin dashboard views (for specific admin operations)
    path('approve-registrations/', views.approve_registrations, name='approve_registrations'),
    path('approve-reports/', views.approve_reports, name='approve_reports'),
    path('suspensions/', views.view_suspensions, name='view_suspensions'),
    path('suspensions/manage/<int:player_id>/', views.manage_suspension, name='manage_suspension'),
    path('statistics/', views.statistics_dashboard, name='statistics_dashboard'),
    path('assign-zones/', views.assign_zones, name='assign_zones'),
    path('view-report/<int:report_id>/', views.view_report, name='view_report'),
    path('generate-fixtures/', admin_views.generate_fixtures_admin, name='generate_fixtures_admin'),
    path('reschedule-fixtures/', reschedule_admin_views.reschedule_fixtures_admin, name='reschedule_fixtures_admin'),
    
    # Activity Logs
    path('activity-logs/', activity_views.activity_logs, name='activity_logs'),
    path('activity-logs/<int:log_id>/', activity_views.activity_log_detail, name='activity_log_detail'),
    path('activity-logs/<int:log_id>/undo/', activity_views.undo_action, name='undo_action'),
    
    # Registration Window Controls
    path('toggle-registration/', views.toggle_registration_window, name='toggle_registration'),
    path('update-deadlines/', views.update_registration_deadlines, name='update_deadlines'),
    
    # Transfer Management
    path('transfers/', views.manage_transfers, name='manage_transfers'),
    path('transfers/override/<int:transfer_id>/', views.admin_override_transfer, name='override_transfer'),
    
    # User Management (Super Admin Only)
    path('users/', views.manage_league_admins, name='manage_league_admins'),
    path('users/create/', views.create_league_admin, name='create_league_admin'),
    path('users/toggle/<int:user_id>/', views.toggle_league_admin_status, name='toggle_league_admin_status'),
    path('users/reset-password/<int:user_id>/', views.reset_league_admin_password, name='reset_league_admin_password'),
    path('users/edit-roles/<int:user_id>/', views.edit_user_roles, name='edit_user_roles'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
]