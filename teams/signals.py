"""
Teams app signals — automatically create teams when disciplines are selected.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import CountyDiscipline, Team, CountyRegistration, County
from competitions.models import SportType


@receiver(post_save, sender=CountyDiscipline)
def auto_create_team_for_discipline(sender, instance, created, **kwargs):
    """
    When a county selects a discipline, automatically create a Team object
    for that county-discipline combination. This ensures teams are registered
    and visible across all views (coordinators, referees, organising secretary, etc.)
    """
    if not created:
        return  # Only on creation, not updates
    
    registration = instance.registration
    county_name = registration.county  # This is a string from KenyaCounty enum
    
    # Get or create the County object
    county_obj, _ = County.objects.get_or_create(
        name=county_name,
        defaults={'code': county_name[:3].upper()}
    )
    
    # Generate team name: "{County} {Sport} {Gender}" e.g. "Makueni Soccer Men"
    SPORT_SHORT_NAMES = {
        'football_men': 'Soccer Men',
        'football_women': 'Soccer Women',
        'volleyball_men': 'Volleyball Men',
        'volleyball_women': 'Volleyball Women',
        'basketball_men': 'Basketball Men',
        'basketball_women': 'Basketball Women',
        'basketball_3x3_men': 'Basketball 3x3 Men',
        'basketball_3x3_women': 'Basketball 3x3 Women',
        'handball_men': 'Handball Men',
        'handball_women': 'Handball Women',
    }
    sport_label = SPORT_SHORT_NAMES.get(instance.sport_type, instance.sport_type)
    team_name = f"{county_name} {sport_label}"
    
    # Check if team already exists for this discipline
    if Team.objects.filter(discipline=instance).exists():
        return
    
    # Create the team
    team = Team.objects.create(
        name=team_name,
        county=county_obj,
        discipline=instance,
        sport_type=instance.sport_type,
        contact_phone=registration.user.phone if registration.user else "",
        status="pending",  # Team starts as pending approval
    )


def ready():
    """Called when the app is ready — import signals."""
    import teams.signals
