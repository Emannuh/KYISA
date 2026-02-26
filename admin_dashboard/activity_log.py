# admin_dashboard/activity_log.py
"""
Activity Logging and Undo System for FKF League Management
Tracks all administrative actions with the ability to undo/rollback changes
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json

User = get_user_model()


class ActivityLog(models.Model):
    """
    Comprehensive activity logging for all system actions
    Supports undo/rollback functionality
    """
    
    ACTION_TYPES = [
        # Team Management
        ('team_approved', 'Team Approved'),
        ('team_rejected', 'Team Rejected'),
        ('team_suspended', 'Team Suspended'),
        ('team_reactivated', 'Team Reactivated'),
        ('team_deleted', 'Team Deleted'),
        
        # Player Management
        ('player_added', 'Player Added'),
        ('player_updated', 'Player Updated'),
        ('player_deleted', 'Player Deleted'),
        ('player_suspended', 'Player Suspended'),
        ('player_unsuspended', 'Player Unsuspended'),
        
        # Match Management
        ('match_created', 'Match Created'),
        ('match_updated', 'Match Updated'),
        ('match_deleted', 'Match Deleted'),
        ('match_result_submitted', 'Match Result Submitted'),
        ('match_result_approved', 'Match Result Approved'),
        ('match_result_rejected', 'Match Result Rejected'),
        ('match_rescheduled', 'Match Rescheduled'),
        
        # Fixture Management
        ('fixtures_generated', 'Fixtures Generated'),
        ('fixtures_regenerated', 'Fixtures Regenerated'),
        ('fixtures_deleted', 'Fixtures Deleted'),
        
        # Transfer Management
        ('transfer_requested', 'Transfer Requested'),
        ('transfer_approved', 'Transfer Approved'),
        ('transfer_rejected', 'Transfer Rejected'),
        ('transfer_overridden', 'Transfer Overridden by Admin'),
        
        # User Management
        ('user_created', 'User Created'),
        ('user_updated', 'User Updated'),
        ('user_deleted', 'User Deleted'),
        ('user_activated', 'User Activated'),
        ('user_deactivated', 'User Deactivated'),
        ('password_reset', 'Password Reset'),
        ('role_changed', 'User Role Changed'),
        
        # Zone Management
        ('zone_created', 'Zone Created'),
        ('zone_updated', 'Zone Updated'),
        ('zone_deleted', 'Zone Deleted'),
        ('team_assigned_zone', 'Team Assigned to Zone'),
        
        # Suspension Management
        ('suspension_created', 'Suspension Created'),
        ('suspension_lifted', 'Suspension Lifted'),
        ('suspension_modified', 'Suspension Modified'),
        
        # Referee Management
        ('referee_assigned', 'Referee Assigned'),
        ('referee_removed', 'Referee Removed'),
        ('report_submitted', 'Match Report Submitted'),
        ('report_approved', 'Match Report Approved'),
        
        # System Actions
        ('settings_updated', 'System Settings Updated'),
        ('registration_opened', 'Registration Window Opened'),
        ('registration_closed', 'Registration Window Closed'),
        
        # Generic
        ('other', 'Other Action'),
    ]
    
    # Who did it
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='activity_logs'
    )
    
    # What was done
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    
    # When it happened
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # IP address and user agent for security
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Store previous state for undo functionality
    previous_state = models.JSONField(null=True, blank=True)
    new_state = models.JSONField(null=True, blank=True)
    
    # Undo tracking
    can_undo = models.BooleanField(default=False)
    is_undone = models.BooleanField(default=False)
    undone_at = models.DateTimeField(null=True, blank=True)
    undone_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='undone_actions'
    )
    undo_reason = models.TextField(blank=True)
    
    # Link to parent action (for tracking undo chains)
    parent_log = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_logs'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"{user_str} - {self.get_action_type_display()} at {self.timestamp}"
    
    def can_be_undone(self):
        """Check if this action can be undone"""
        if self.is_undone:
            return False
        if not self.can_undo:
            return False
        # Check if enough time has passed (optional safety check)
        # Can add time-based restrictions here
        return True
    
    def get_affected_object(self):
        """Get the object affected by this action"""
        if self.content_object:
            return self.content_object
        return None


class UndoHistory(models.Model):
    """
    Track undo operations for audit trail
    """
    original_log = models.ForeignKey(
        ActivityLog,
        on_delete=models.CASCADE,
        related_name='undo_history'
    )
    undone_by = models.ForeignKey(User, on_delete=models.CASCADE)
    undone_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-undone_at']
    
    def __str__(self):
        return f"Undo of {self.original_log} by {self.undone_by}"


# Helper functions for logging
def log_activity(user, action_type, description, obj=None, 
                 previous_state=None, new_state=None, 
                 can_undo=False, request=None):
    """
    Convenience function to log an activity
    
    Args:
        user: User performing the action
        action_type: Type of action (from ACTION_TYPES)
        description: Human-readable description
        obj: The object being affected (optional)
        previous_state: Dict of previous values (for undo)
        new_state: Dict of new values
        can_undo: Whether this action can be undone
        request: HTTP request object (for IP/user agent)
    """
    log = ActivityLog(
        user=user,
        action_type=action_type,
        description=description,
        previous_state=previous_state,
        new_state=new_state,
        can_undo=can_undo
    )
    
    if obj:
        log.content_object = obj
    
    if request:
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            log.ip_address = x_forwarded_for.split(',')[0]
        else:
            log.ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        log.user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    log.save()
    return log


def undo_action(log_id, user, reason=""):
    """
    Attempt to undo an action
    
    Args:
        log_id: ID of the ActivityLog to undo
        user: User performing the undo
        reason: Reason for undoing
    
    Returns:
        (success, message) tuple
    """
    try:
        log = ActivityLog.objects.get(id=log_id)
        
        if not log.can_be_undone():
            return False, "This action cannot be undone"
        
        if log.is_undone:
            return False, "This action has already been undone"
        
        # Perform the undo based on action type
        success, message = _perform_undo(log)
        
        if success:
            # Mark as undone
            log.is_undone = True
            log.undone_at = timezone.now()
            log.undone_by = user
            log.undo_reason = reason
            log.save()
            
            # Create undo history record
            UndoHistory.objects.create(
                original_log=log,
                undone_by=user,
                reason=reason,
                success=True
            )
            
            return True, message
        else:
            # Log failed undo attempt
            UndoHistory.objects.create(
                original_log=log,
                undone_by=user,
                reason=reason,
                success=False,
                error_message=message
            )
            return False, message
            
    except ActivityLog.DoesNotExist:
        return False, "Activity log not found"
    except Exception as e:
        return False, f"Error during undo: {str(e)}"


def _perform_undo(log):
    """
    Internal function to perform the actual undo operation
    Returns (success, message)
    """
    from teams.models import Team, Player
    from matches.models import Match
    
    try:
        if log.action_type == 'team_approved':
            # Revert team to pending
            team = log.content_object
            if team and hasattr(team, 'status'):
                team.status = log.previous_state.get('status', 'pending')
                team.save()
                return True, f"Team {team.team_name} reverted to {team.status}"
        
        elif log.action_type == 'team_rejected':
            # Revert team to previous status
            team = log.content_object
            if team and hasattr(team, 'status'):
                team.status = log.previous_state.get('status', 'pending')
                team.save()
                return True, f"Team {team.team_name} status restored"
        
        elif log.action_type == 'fixtures_generated':
            # Delete generated fixtures
            from teams.models import Zone
            zone = log.content_object
            if zone:
                Match.objects.filter(zone=zone).delete()
                zone.fixtures_generated = False
                zone.fixture_generation_date = None
                zone.save()
                return True, f"Fixtures deleted for {zone.name}"
        
        elif log.action_type == 'player_suspended':
            # Lift suspension
            from matches.models import Suspension
            player = log.content_object
            if player:
                Suspension.objects.filter(player=player, is_active=True).update(is_active=False)
                return True, f"Suspension lifted for {player.full_name}"
        
        elif log.action_type == 'user_deactivated':
            # Reactivate user
            user_obj = log.content_object
            if user_obj and hasattr(user_obj, 'is_active'):
                user_obj.is_active = True
                user_obj.save()
                return True, f"User {user_obj.username} reactivated"
        
        elif log.action_type == 'transfer_approved':
            # Reverse transfer
            transfer = log.content_object
            if transfer and hasattr(transfer, 'status'):
                transfer.status = 'pending'
                transfer.save()
                # Restore player to original team
                if log.previous_state and 'player_team' in log.previous_state:
                    player = transfer.player
                    old_team_id = log.previous_state['player_team']
                    from teams.models import Team
                    old_team = Team.objects.get(id=old_team_id)
                    player.team = old_team
                    player.save()
                return True, f"Transfer reversed for {transfer.player.full_name}"
        
        # Add more undo handlers as needed
        
        return False, "Undo operation not implemented for this action type"
        
    except Exception as e:
        return False, f"Error performing undo: {str(e)}"
