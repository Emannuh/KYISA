"""
KYISA Teams — Django Forms for Registration & Management
Adapted from FKFSYS teams registration workflow.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Team, Player, PLAYER_MIN_AGE, PLAYER_MAX_AGE


class TeamRegistrationForm(forms.ModelForm):
    """
    Public team registration form.
    Creates a team with 'pending' status awaiting admin approval.
    """

    class Meta:
        model = Team
        fields = [
            'name', 'county', 'contact_phone', 'contact_email',
            'home_colour', 'away_colour', 'badge',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter team name',
                'required': True,
            }),
            'county': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Laikipia',
                'required': True,
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678',
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'team@example.com',
            }),
            'home_colour': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Green',
            }),
            'away_colour': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. White',
            }),
            'badge': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }
        labels = {
            'name': 'Team Name *',
            'county': 'County *',
            'contact_phone': 'Contact Phone',
            'contact_email': 'Contact Email',
            'home_colour': 'Home Kit Colour',
            'away_colour': 'Away Kit Colour',
            'badge': 'Team Badge / Logo',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Team.objects.filter(name__iexact=name).exists():
            raise ValidationError(f'A team named "{name}" already exists.')
        return name

    def clean_contact_email(self):
        email = self.cleaned_data.get('contact_email')
        if email and Team.objects.filter(contact_email=email).exists():
            raise ValidationError('This email is already registered to another team.')
        return email


class PlayerRegistrationForm(forms.ModelForm):
    """
    Player registration form — used after a team is approved.
    Includes document upload fields and age validation.
    """

    class Meta:
        model = Player
        fields = [
            'first_name', 'last_name', 'date_of_birth',
            'position', 'shirt_number',
            'national_id_number', 'birth_cert_number',
            'photo', 'id_document', 'birth_certificate',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'position': forms.Select(attrs={
                'class': 'form-control',
            }),
            'shirt_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '99',
            }),
            'national_id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 12345678',
            }),
            'birth_cert_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 0123456789',
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'id_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf',
            }),
            'birth_certificate': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf',
            }),
        }
        labels = {
            'first_name': 'First Name *',
            'last_name': 'Last Name *',
            'date_of_birth': 'Date of Birth *',
            'position': 'Position *',
            'shirt_number': 'Shirt Number *',
            'national_id_number': 'National ID Number',
            'birth_cert_number': 'Birth Certificate Number',
            'photo': 'Passport-Size Photo *',
            'id_document': 'Copy of National ID *',
            'birth_certificate': 'Copy of Birth Certificate *',
        }
        help_texts = {
            'photo': 'Clear passport-size photograph',
            'id_document': 'Scan or photo of the player\'s National ID',
            'birth_certificate': 'Scan or photo of the player\'s Birth Certificate',
            'date_of_birth': f'Player must be between {PLAYER_MIN_AGE} and {PLAYER_MAX_AGE} years old',
        }

    def clean_date_of_birth(self):
        """Validate age is within the 18-23 bracket."""
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = timezone.now().date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < PLAYER_MIN_AGE:
                raise ValidationError(
                    f'Player is {age} years old. Minimum age is {PLAYER_MIN_AGE}. '
                    f'Registration is not allowed.'
                )
            if age > PLAYER_MAX_AGE:
                raise ValidationError(
                    f'Player is {age} years old. Maximum age is {PLAYER_MAX_AGE}. '
                    f'Registration is not allowed.'
                )
        return dob
