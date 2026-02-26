# admin_dashboard/views.py — Adapted for KYISA CMS models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.core.mail import send_mail
from django.conf import settings as django_settings

from accounts.models import User, UserRole
from teams.models import Team, Player
from referees.models import RefereeProfile, RefereeAppointment
from competitions.models import Competition, Fixture
from matches.models import MatchReport


def admin_required(user):
    """Check if user is superuser, staff, or admin role"""
    return user.is_superuser or user.is_staff or user.role == 'admin'


def superadmin_required(user):
    """Check if user is superuser"""
    return user.is_superuser


def send_welcome_email(user_obj, password, role):
    """Send welcome email to newly created user with login credentials."""
    from django.core.mail import EmailMultiAlternatives

    subject = f'Welcome to KYISA Competition Management System - {role}'
    text_content = f"""
Dear {user_obj.first_name} {user_obj.last_name},

Welcome to the KYISA Competition Management System!

Your account has been created:

Login Email: {user_obj.email}
Temporary Password: {password}
Role: {role}

Login URL: /portal/login/

Please change your password after your first login.

Best regards,
KYISA Administration
"""
    try:
        email = EmailMultiAlternatives(
            subject, text_content,
            getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@kyisa.org'),
            [user_obj.email]
        )
        email.send(fail_silently=True)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_password_reset_email(user_obj, new_password):
    """Send password reset email."""
    from django.core.mail import EmailMultiAlternatives

    subject = 'KYISA CMS - Password Reset'
    text_content = f"""
Dear {user_obj.first_name} {user_obj.last_name},

Your password has been reset by an administrator.

Login Email: {user_obj.email}
New Password: {new_password}

Please change your password immediately after login.

Best regards,
KYISA Administration
"""
    try:
        email = EmailMultiAlternatives(
            subject, text_content,
            getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@kyisa.org'),
            [user_obj.email]
        )
        email.send(fail_silently=True)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#   ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(admin_required)
def admin_dashboard(request):
    """Main admin dashboard with KYISA statistics."""
    total_teams = Team.objects.count()
    registered_teams = Team.objects.filter(status='registered').count()
    pending_teams_count = Team.objects.filter(status='pending').count()
    total_players = Player.objects.count()
    total_referees = RefereeProfile.objects.count()
    approved_referees = RefereeProfile.objects.filter(is_approved=True).count()
    pending_referees_count = RefereeProfile.objects.filter(is_approved=False).count()
    total_competitions = Competition.objects.count()
    total_fixtures = Fixture.objects.count()

    # Recent activities
    recent_teams = Team.objects.order_by('-registered_at')[:5]
    recent_fixtures = Fixture.objects.select_related(
        'competition', 'home_team', 'away_team'
    ).order_by('-match_date')[:5]

    context = {
        'total_teams': total_teams,
        'registered_teams': registered_teams,
        'pending_teams': pending_teams_count,
        'total_players': total_players,
        'total_referees': total_referees,
        'approved_referees': approved_referees,
        'pending_referees': pending_referees_count,
        'total_competitions': total_competitions,
        'total_fixtures': total_fixtures,
        'recent_teams': recent_teams,
        'recent_fixtures': recent_fixtures,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
#   TEAM REGISTRATION APPROVAL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(admin_required)
def approve_registrations(request):
    """Approve/reject team registrations and create manager accounts."""
    pending_teams_qs = Team.objects.filter(status='pending').order_by('-registered_at')

    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        action = request.POST.get('action')
        team = get_object_or_404(Team, id=team_id)

        if action == 'approve':
            team.status = 'registered'
            team.save()

            # Create manager account if contact email exists and no manager linked
            if team.contact_email and not team.manager:
                try:
                    # Check if user with this email already exists
                    if User.objects.filter(email=team.contact_email).exists():
                        mgr = User.objects.get(email=team.contact_email)
                        team.manager = mgr
                        team.save()
                        messages.success(request, mark_safe(
                            f'<strong>{team.name}</strong> approved!<br>'
                            f'Linked to existing user: {team.contact_email}'
                        ))
                    else:
                        import secrets, string as _s
                        default_pw = ''.join(secrets.choice(_s.ascii_letters + _s.digits) for _ in range(10))
                        mgr = User.objects.create_user(
                            email=team.contact_email,
                            password=default_pw,
                            first_name=team.name,
                            last_name='Manager',
                            role=UserRole.TEAM_MANAGER,
                            county=team.county,
                        )
                        team.manager = mgr
                        team.save()

                        # Try sending email
                        send_welcome_email(mgr, default_pw, 'Team Manager')

                        messages.success(request, mark_safe(
                            f'<strong>{team.name}</strong> approved!<br>'
                            f'Manager account: <code>{team.contact_email}</code><br>'
                            f'Temp password: <code>{default_pw}</code>'
                        ))
                except Exception as e:
                    messages.warning(request, f'Team approved but manager account failed: {e}')
            else:
                messages.success(request, f'{team.name} has been approved.')

        elif action == 'reject':
            team.status = 'suspended'
            team.save()
            messages.warning(request, f'{team.name} registration rejected.')

        return redirect('approve_registrations')

    return render(request, 'admin_dashboard/approve_registrations.html', {
        'pending_teams': pending_teams_qs,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   MATCH REPORT APPROVAL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(admin_required)
def approve_reports(request):
    """Approve match reports."""
    pending_reports = MatchReport.objects.filter(
        status='submitted'
    ).order_by('-submitted_at')

    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        action = request.POST.get('action')
        report = get_object_or_404(MatchReport, id=report_id)

        if action == 'approve':
            report.status = 'approved'
            report.save()
            messages.success(request, f'Report approved.')
        elif action == 'reject':
            report.status = 'rejected'
            report.save()
            messages.warning(request, f'Report rejected.')

        return redirect('approve_reports')

    return render(request, 'admin_dashboard/approve_reports.html', {
        'pending_reports': pending_reports,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   PLAYER SUSPENSIONS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(admin_required)
def view_suspensions(request):
    """View suspended players."""
    suspended_players = Player.objects.filter(status='suspended')
    context = {
        'suspended_players': suspended_players,
    }
    return render(request, 'admin_dashboard/suspensions.html', context)


@login_required
@user_passes_test(admin_required)
def manage_suspension(request, player_id):
    """Manage player suspension."""
    player = get_object_or_404(Player, id=player_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'suspend':
            player.status = 'suspended'
            player.save()
            messages.success(request, f'{player.get_full_name()} suspended.')

        elif action == 'clear':
            player.status = 'eligible'
            player.save()
            messages.success(request, f'{player.get_full_name()} suspension cleared.')

        return redirect('view_suspensions')

    return render(request, 'admin_dashboard/manage_suspension.html', {
        'player': player,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   STATISTICS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(admin_required)
def statistics_dashboard(request):
    """Statistics and analytics dashboard."""
    # Team stats by county
    county_stats = (
        Team.objects.filter(status='registered')
        .values('county')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Player position distribution
    position_stats = (
        Player.objects.values('position')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Referee level distribution
    referee_stats = (
        RefereeProfile.objects.filter(is_approved=True)
        .values('level')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Competition stats
    competition_stats = {
        'total': Competition.objects.count(),
        'active': Competition.objects.filter(status='active').count(),
        'completed': Competition.objects.filter(status='completed').count(),
    }

    context = {
        'county_stats': county_stats,
        'position_stats': position_stats,
        'referee_stats': referee_stats,
        'competition_stats': competition_stats,
        'total_teams': Team.objects.filter(status='registered').count(),
        'total_players': Player.objects.count(),
        'total_referees': RefereeProfile.objects.filter(is_approved=True).count(),
    }
    return render(request, 'admin_dashboard/statistics.html', context)


# ══════════════════════════════════════════════════════════════════════════════
#   COMPETITION ASSIGNMENT (replaces FKFSYS Zone assignment)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(admin_required)
def assign_zones(request):
    """Assign teams to competitions (KYISA equivalent of zone assignment)."""
    unassigned_teams = Team.objects.filter(
        status='registered',
        competition__isnull=True
    ).order_by('name')

    competitions = Competition.objects.all()

    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        comp_id = request.POST.get('competition_id')

        team = get_object_or_404(Team, id=team_id)
        comp = get_object_or_404(Competition, id=comp_id) if comp_id else None

        team.competition = comp
        team.save()

        messages.success(request, f'{team.name} assigned to {comp.name if comp else "None"}.')
        return redirect('assign_zones')

    # Get assignments
    comp_assignments = {}
    for comp in competitions:
        comp_assignments[comp] = Team.objects.filter(competition=comp, status='registered')

    return render(request, 'admin_dashboard/assign_zones.html', {
        'teams': unassigned_teams,
        'competitions': competitions,
        'comp_assignments': comp_assignments,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   VIEW MATCH REPORT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def view_report(request, report_id):
    """View a specific match report in detail."""
    report = get_object_or_404(MatchReport, id=report_id)

    if not request.user.is_staff and not request.user.is_superuser:
        if hasattr(report, 'referee') and report.referee and hasattr(report.referee, 'user'):
            if report.referee.user != request.user:
                messages.error(request, "Permission denied.")
                return redirect('dashboard')

    return render(request, 'admin_dashboard/view_report.html', {
        'report': report,
        'title': f'Match Report #{report.id}',
    })


# ══════════════════════════════════════════════════════════════════════════════
#   USER MANAGEMENT (Super Admin Only)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(superadmin_required)
def manage_league_admins(request):
    """Manage all users — filter, search, view."""
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')

    users = User.objects.all()

    if role_filter != 'all':
        users = users.filter(role=role_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    users = users.order_by('-date_joined')

    user_stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
        'team_managers': User.objects.filter(role='team_manager').count(),
        'admins': User.objects.filter(role='admin').count(),
        'referees': User.objects.filter(role='referee').count(),
        'referee_managers': User.objects.filter(role='referee_manager').count(),
        'competition_managers': User.objects.filter(role='competition_manager').count(),
    }

    context = {
        'users': users,
        'user_stats': user_stats,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'role_choices': UserRole.choices,
    }
    return render(request, 'admin_dashboard/manage_league_admins.html', context)


@login_required
@user_passes_test(superadmin_required)
def create_league_admin(request):
    """Create a new user with selected role."""
    import random, string

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', 'team_manager')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' already registered.")
            return redirect('manage_league_admins')

        try:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            user_obj = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
            )
            send_welcome_email(user_obj, password, role)
            messages.success(request, mark_safe(
                f'User created!<br>'
                f'Email: <code>{email}</code><br>'
                f'Password: <code>{password}</code><br>'
                f'Role: {role}'
            ))
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return redirect('manage_league_admins')


@login_required
@user_passes_test(superadmin_required)
def toggle_league_admin_status(request, user_id):
    """Activate or deactivate a user."""
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj == request.user:
        messages.error(request, "Cannot deactivate your own account!")
        return redirect('manage_league_admins')

    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    status = "activated" if user_obj.is_active else "deactivated"
    messages.success(request, f"{user_obj.email} has been {status}.")
    return redirect('manage_league_admins')


@login_required
@user_passes_test(superadmin_required)
def reset_league_admin_password(request, user_id):
    """Reset password for any user."""
    import random, string

    user_obj = get_object_or_404(User, id=user_id)
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    user_obj.set_password(new_password)
    user_obj.save()

    send_password_reset_email(user_obj, new_password)
    messages.success(request, mark_safe(
        f'Password reset for {user_obj.email}.<br>'
        f'New password: <code>{new_password}</code>'
    ))
    return redirect('manage_league_admins')


@login_required
@user_passes_test(superadmin_required)
def edit_user_roles(request, user_id):
    """Edit user's role assignment."""
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_role = request.POST.get('role', user_obj.role)
        user_obj.role = new_role
        user_obj.save()
        messages.success(request, f"Role updated for {user_obj.email} to {new_role}.")
        return redirect('manage_league_admins')

    context = {
        'edit_user': user_obj,
        'role_choices': UserRole.choices,
    }
    return render(request, 'admin_dashboard/edit_user_roles.html', context)


@login_required
@user_passes_test(superadmin_required)
def delete_user(request, user_id):
    """Delete a user account."""
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj == request.user:
        messages.error(request, "Cannot delete your own account!")
        return redirect('manage_league_admins')

    if user_obj.is_superuser:
        messages.error(request, "Cannot delete superuser accounts!")
        return redirect('manage_league_admins')

    email = user_obj.email
    user_obj.delete()
    messages.success(request, f"User '{email}' deleted.")
    return redirect('manage_league_admins')


# ══════════════════════════════════════════════════════════════════════════════
#   PLACEHOLDER VIEWS for features referenced in urls.py
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(admin_required)
def toggle_registration_window(request):
    """Placeholder: Toggle registration windows (future feature)."""
    messages.info(request, "Registration window control coming soon.")
    return redirect('dashboard')


@login_required
@user_passes_test(admin_required)
def update_registration_deadlines(request):
    """Placeholder: Update registration deadlines (future feature)."""
    messages.info(request, "Deadline management coming soon.")
    return redirect('dashboard')


@login_required
@user_passes_test(admin_required)
def manage_transfers(request):
    """Placeholder: Transfer management (future feature)."""
    messages.info(request, "Transfer system coming soon.")
    return redirect('dashboard')


@login_required
@user_passes_test(admin_required)
def admin_override_transfer(request, transfer_id):
    """Placeholder: Transfer override (future feature)."""
    messages.info(request, "Transfer system coming soon.")
    return redirect('dashboard')
