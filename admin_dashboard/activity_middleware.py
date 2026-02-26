# admin_dashboard/activity_middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog
import json


class ActivityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log user activities across the system
    """
    
    # Actions that should be logged
    LOGGED_PATHS = {
        # Authentication
        '/accounts/login/': 'LOGIN',
        '/accounts/logout/': 'LOGOUT',
        
        # Team Management
        '/teams/register/': 'TEAM_CREATE',
        '/teams/edit/': 'TEAM_UPDATE',
        '/teams/delete/': 'TEAM_DELETE',
        
        # Player Management
        '/teams/player/add/': 'PLAYER_CREATE',
        '/teams/player/edit/': 'PLAYER_UPDATE',
        '/teams/player/delete/': 'PLAYER_DELETE',
        '/teams/player/transfer/': 'PLAYER_TRANSFER',
        
        # Match Management
        '/matches/create/': 'MATCH_CREATE',
        '/matches/edit/': 'MATCH_UPDATE',
        '/matches/reschedule/': 'MATCH_RESCHEDULE',
        
        # Match Reports
        '/referees/match/': 'MATCH_REPORT',
        
        # Fixture Management
        '/admin-dashboard/generate-fixtures/': 'FIXTURE_GENERATE',
        
        # Squad Management
        '/referees/matchday/squad/submit/': 'SQUAD_SUBMIT',
        '/referees/matchday/referee/approve/': 'SQUAD_APPROVE',
        
        # Referee Management
        '/referees/match/': 'REFEREE_ACTION',
        '/referees/register/': 'REFEREE_REGISTER',
        
        # Payment Management
        '/payments/': 'PAYMENT_ACTION',
        
        # Admin Actions
        '/admin-dashboard/': 'ADMIN_ACTION',
    }
    
    def process_response(self, request, response):
        """Log activity after successful requests"""
        
        # Only log for authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Only log POST requests (actions that change data)
        if request.method != 'POST':
            return response
        
        # Only log successful responses (200-399)
        if not (200 <= response.status_code < 400):
            return response
        
        # Get the action type based on path
        action = self._get_action_type(request.path)
        if not action:
            return response
        
        # Get description
        description = self._generate_description(request, action)
        
        # Get IP address
        ip_address = self._get_client_ip(request)
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Create activity log
        try:
            ActivityLog.objects.create(
                user=request.user,
                action=action,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                changes_json=self._get_changes_json(request)
            )
        except Exception as e:
            # Don't break the request if logging fails
            print(f"Activity logging error: {e}")
        
        return response
    
    def _get_action_type(self, path):
        """Determine action type from request path"""
        for path_pattern, action in self.LOGGED_PATHS.items():
            if path_pattern in path:
                # Special handling for specific actions
                if 'login' in path:
                    return 'LOGIN'
                elif 'logout' in path:
                    return 'LOGOUT'
                elif 'generate-fixtures' in path:
                    return 'FIXTURE_GENERATE' if 'regenerate' not in path else 'FIXTURE_REGENERATE'
                elif 'approve' in path:
                    return 'SQUAD_APPROVE'
                elif 'submit' in path and 'squad' in path:
                    return 'MATCHDAY_SQUAD_SUBMIT'
                elif 'comprehensive-report' in path:
                    return 'MATCH_REPORT'
                elif 'reschedule' in path:
                    return 'MATCH_RESCHEDULE'
                elif 'transfer' in path:
                    return 'PLAYER_TRANSFER'
                elif 'register' in path and 'teams' in path:
                    return 'TEAM_CREATE'
                elif 'register' in path and 'referee' in path:
                    return 'REFEREE_REGISTER'
                else:
                    return action
        return None
    
    def _generate_description(self, request, action):
        """Generate human-readable description of the action"""
        user = request.user
        path = request.path
        
        descriptions = {
            'LOGIN': f'{user.username} logged into the system',
            'LOGOUT': f'{user.username} logged out',
            'FIXTURE_GENERATE': f'{user.username} generated fixtures',
            'FIXTURE_REGENERATE': f'{user.username} regenerated fixtures',
            'SQUAD_APPROVE': f'{user.username} approved matchday squad',
            'MATCHDAY_SQUAD_SUBMIT': f'{user.username} submitted matchday squad',
            'MATCH_REPORT': f'{user.username} submitted/updated match report',
            'TEAM_CREATE': f'{user.username} registered a new team',
            'TEAM_UPDATE': f'{user.username} updated team information',
            'PLAYER_CREATE': f'{user.username} added a new player',
            'PLAYER_UPDATE': f'{user.username} updated player information',
            'PLAYER_TRANSFER': f'{user.username} processed player transfer',
            'MATCH_RESCHEDULE': f'{user.username} rescheduled a match',
            'REFEREE_REGISTER': f'{user.username} registered as referee',
        }
        
        return descriptions.get(action, f'{user.username} performed {action} at {path}')
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip[:45]  # Max length of IP field
    
    def _get_changes_json(self, request):
        """Extract relevant data from POST request"""
        try:
            # Get POST data (excluding sensitive fields)
            sensitive_fields = ['password', 'csrfmiddlewaretoken', 'password1', 'password2']
            data = {
                key: value for key, value in request.POST.items()
                if key not in sensitive_fields and not key.startswith('_')
            }
            
            # Limit size
            data_str = json.dumps(data, default=str)
            if len(data_str) > 5000:
                return json.dumps({'note': 'Data too large to store'})
            
            return data_str
        except Exception:
            return '{}'
