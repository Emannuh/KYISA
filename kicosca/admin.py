from django.contrib import admin
from django.utils.html import format_html

from .models import (
    KicoscaEdition,
    KicoscaCountyEntry,
    KicoscaDiscipline,
    KicoscaPlayer,
)


# ── Inline: Disciplines inside a County Entry ─────────────────────────────────
class KicoscaDisciplineInline(admin.TabularInline):
    model  = KicoscaDiscipline
    extra  = 0
    fields = ["sport", "player_count_display", "squad_limit"]
    readonly_fields = ["player_count_display", "squad_limit"]

    def player_count_display(self, obj):
        return obj.player_count
    player_count_display.short_description = "Players registered"


# ── Inline: County Entries inside an Edition ─────────────────────────────────
class KicoscaCountyEntryInline(admin.TabularInline):
    model  = KicoscaCountyEntry
    extra  = 0
    fields = ["county_registration"]


# ── KicoscaEdition ────────────────────────────────────────────────────────────
@admin.register(KicoscaEdition)
class KicoscaEditionAdmin(admin.ModelAdmin):
    list_display  = ["name", "year", "host_county", "start_date", "end_date", "is_active", "entry_count"]
    list_filter   = ["is_active", "year"]
    search_fields = ["name", "host_county"]
    inlines       = [KicoscaCountyEntryInline]

    def entry_count(self, obj):
        return obj.county_entries.count()
    entry_count.short_description = "Counties entered"


# ── KicoscaCountyEntry ────────────────────────────────────────────────────────
@admin.register(KicoscaCountyEntry)
class KicoscaCountyEntryAdmin(admin.ModelAdmin):
    list_display  = ["county", "edition", "discipline_count"]
    list_filter   = ["edition", "county_registration__county"]
    search_fields = ["county_registration__county"]
    inlines       = [KicoscaDisciplineInline]

    def discipline_count(self, obj):
        return obj.disciplines.count()
    discipline_count.short_description = "Disciplines"


# ── KicoscaDiscipline ─────────────────────────────────────────────────────────
@admin.register(KicoscaDiscipline)
class KicoscaDisciplineAdmin(admin.ModelAdmin):
    list_display  = ["__str__", "sport", "player_count", "squad_limit"]
    list_filter   = ["sport", "entry__edition", "entry__county_registration__county"]
    search_fields = ["entry__county_registration__county"]


# ── KicoscaPlayer ─────────────────────────────────────────────────────────────
@admin.register(KicoscaPlayer)
class KicoscaPlayerAdmin(admin.ModelAdmin):
    list_display = [
        "full_name", "county_display", "sport_display",
        "national_id_number", "kra_pin",
        "prembly_badge", "kra_badge", "verification_status",
        "registered_at",
    ]
    list_filter  = [
        "verification_status",
        "prembly_status",
        "kra_employment_status",
        "discipline__sport",
        "discipline__entry__edition",
        "discipline__entry__county_registration__county",
    ]
    search_fields = [
        "first_name", "last_name",
        "national_id_number", "kra_pin",
        "discipline__entry__county_registration__county",
    ]
    readonly_fields = [
        "prembly_status", "prembly_verified_name", "prembly_reference", "prembly_checked_at",
        "kra_employment_status", "kra_employer_name", "kra_employer_pin",
        "kra_verification_ref", "kra_checked_at", "kra_raw_response",
        "verified_by", "verified_at", "registered_at",
    ]
    fieldsets = (
        ("Personal Details", {
            "fields": (
                "discipline",
                ("first_name", "last_name"),
                "date_of_birth",
                ("national_id_number", "kra_pin"),
                "phone",
                ("department", "employee_number", "position_title"),
                ("jersey_number", "sport_position"),
            ),
        }),
        ("Documents", {
            "fields": ("photo", "id_document", "payslip", "appointment_letter", "iprs_photo"),
        }),
        ("IPRS Identity Verification (Prembly)", {
            "classes": ("collapse",),
            "fields": (
                "prembly_status", "prembly_verified_name",
                "prembly_reference", "prembly_checked_at",
            ),
        }),
        ("KRA Employment Verification", {
            "classes": ("collapse",),
            "fields": (
                "kra_employment_status", "kra_employer_name", "kra_employer_pin",
                "kra_verification_ref", "kra_checked_at", "kra_raw_response",
            ),
        }),
        ("Overall Verification", {
            "fields": (
                "verification_status", "rejection_reason",
                "verified_by", "verified_at",
            ),
        }),
    )

    def county_display(self, obj):
        return obj.discipline.entry.county_registration.county
    county_display.short_description = "County"

    def sport_display(self, obj):
        return obj.discipline.get_sport_display()
    sport_display.short_description = "Sport"

    def prembly_badge(self, obj):
        colours = {
            "verified":    ("✅", "green"),
            "failed":      ("❌", "red"),
            "mismatch":    ("⚠️", "orange"),
            "not_checked": ("—", "grey"),
        }
        icon, colour = colours.get(obj.prembly_status, ("?", "grey"))
        return format_html(
            '<span style="color:{}">{} {}</span>',
            colour, icon, obj.get_prembly_status_display(),
        )
    prembly_badge.short_description = "IPRS (Prembly)"

    def kra_badge(self, obj):
        colours = {
            "verified":    ("✅", "green"),
            "failed":      ("❌", "red"),
            "mismatch":    ("⚠️", "orange"),
            "not_checked": ("—", "grey"),
            "pending":     ("🕐", "blue"),
        }
        icon, colour = colours.get(obj.kra_employment_status, ("?", "grey"))
        return format_html(
            '<span style="color:{}">{} {}</span>',
            colour, icon, obj.get_kra_employment_status_display(),
        )
    kra_badge.short_description = "KRA Employment"
