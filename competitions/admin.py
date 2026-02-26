from django.contrib import admin
from .models import Competition, Venue, Pool, PoolTeam, Fixture


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display  = ["name", "season", "age_group", "status", "start_date", "end_date"]
    list_filter   = ["status", "age_group", "season"]
    search_fields = ["name"]


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ["name", "county", "city", "capacity", "surface", "is_active"]
    list_filter  = ["county", "is_active"]
    search_fields = ["name", "city"]


class PoolTeamInline(admin.TabularInline):
    model  = PoolTeam
    extra  = 0
    fields = ["team", "played", "won", "drawn", "lost", "goals_for", "goals_against"]


@admin.register(Pool)
class PoolAdmin(admin.ModelAdmin):
    list_display = ["name", "competition"]
    list_filter  = ["competition"]
    inlines      = [PoolTeamInline]


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display  = ["__str__", "competition", "match_date", "kickoff_time", "venue", "status"]
    list_filter   = ["status", "competition", "match_date"]
    search_fields = ["home_team__name", "away_team__name"]
    date_hierarchy = "match_date"
