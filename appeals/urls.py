"""
KYISA Appeals — URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    # ── Appeal listing & dashboard ────────────────────────────────────────
    path("",                                      views.appeals_list_view,              name="appeals_list"),
    path("jury-dashboard/",                       views.jury_dashboard_view,            name="jury_dashboard"),

    # ── Appeal CRUD ───────────────────────────────────────────────────────
    path("new/",                                  views.submit_appeal_view,             name="submit_appeal"),
    path("<int:pk>/",                             views.appeal_detail_view,             name="appeal_detail"),
    path("<int:pk>/evidence/",                    views.upload_evidence_view,           name="upload_appeal_evidence"),
    path("<int:pk>/pay-fee/",                     views.pay_fee_view,                   name="pay_appeal_fee"),
    path("<int:pk>/submit/",                      views.finalize_appeal_view,           name="finalize_appeal"),

    # ── Response ──────────────────────────────────────────────────────────
    path("<int:pk>/respond/",                     views.submit_response_view,           name="submit_appeal_response"),
    path("<int:pk>/respond/evidence/",            views.upload_response_evidence_view,  name="upload_response_evidence"),

    # ── Jury decisions ────────────────────────────────────────────────────
    path("<int:pk>/decision/",                    views.jury_decision_view,             name="jury_decision"),
    path("<int:pk>/decision/<int:decision_pk>/evidence/",  views.upload_decision_evidence_view, name="upload_decision_evidence"),
    path("<int:pk>/decision/<int:decision_pk>/publish/",   views.publish_decision_view,         name="publish_decision"),

    # ── Re-appeal ─────────────────────────────────────────────────────────
    path("<int:pk>/reappeal/",                    views.reappeal_view,                  name="reappeal"),

    # ── Fee verification (admin/treasurer) ────────────────────────────────
    path("<int:pk>/verify-fee/",                  views.verify_fee_view,                name="verify_appeal_fee"),
]
