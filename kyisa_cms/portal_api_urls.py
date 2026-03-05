"""
Portal API URL patterns — /api/v1/portal/
"""
from django.urls import path
from .portal_api_views import (
    PortalDashboardView,
    ClearanceListView,
    ClearanceDetailView,
    ClearanceGrantView,
    ClearanceRejectView,
    TreasurerPaymentsView,
    PaymentVerifyView,
    PaymentRejectView,
    AdminDashboardView,
    ActivityLogListView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/', PortalDashboardView.as_view(), name='portal-dashboard'),

    # Clearance / Verification
    path('clearance/', ClearanceListView.as_view(), name='portal-clearance-list'),
    path('clearance/<int:pk>/', ClearanceDetailView.as_view(), name='portal-clearance-detail'),
    path('clearance/<int:pk>/grant/', ClearanceGrantView.as_view(), name='portal-clearance-grant'),
    path('clearance/<int:pk>/reject/', ClearanceRejectView.as_view(), name='portal-clearance-reject'),

    # Treasurer
    path('treasurer/payments/', TreasurerPaymentsView.as_view(), name='portal-treasurer-payments'),
    path('treasurer/payments/<int:pk>/verify/', PaymentVerifyView.as_view(), name='portal-payment-verify'),
    path('treasurer/payments/<int:pk>/reject/', PaymentRejectView.as_view(), name='portal-payment-reject'),

    # Admin
    path('admin/dashboard/', AdminDashboardView.as_view(), name='portal-admin-dashboard'),
    path('admin/activity-logs/', ActivityLogListView.as_view(), name='portal-activity-logs'),
]
