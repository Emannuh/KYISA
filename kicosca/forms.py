from django import forms
from accounts.models import kenya_phone_validator
from .models import KicoscaPlayer


def validate_kenya_phone(value):
    """Accept +254XXXXXXXXX or 07XXXXXXXX or 01XXXXXXXX."""
    import re
    v = value.strip()
    if re.match(r'^\+254\d{9}$', v):
        return v
    if re.match(r'^0[17]\d{8}$', v):
        return '+254' + v[1:]
    raise forms.ValidationError(
        'Enter a valid Kenyan phone number (e.g. +254712345678 or 0712345678).'
    )


class KicoscaPlayerForm(forms.ModelForm):
    """
    Form for county sports director to register a KICOSCA player.
    National ID lookup via Prembly IPRS is handled by JS on the page.
    KRA PIN employment check is run separately after saving.
    """

    class Meta:
        model  = KicoscaPlayer
        fields = [
            'first_name', 'last_name', 'date_of_birth',
            'national_id_number', 'kra_pin', 'phone',
            'department', 'employee_number', 'position_title',
            'sport_position', 'jersey_number',
            'photo', 'id_document', 'payslip', 'appointment_letter',
        ]
        widgets = {
            'first_name':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'date_of_birth':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 12345678', 'maxlength': '8'}),
            'kra_pin':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A001234567B', 'maxlength': '11', 'style': 'font-family:monospace;text-transform:uppercase'}),
            'phone':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254712345678'}),
            'department':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Department of Finance'}),
            'employee_number':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP/2024/001'}),
            'position_title':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Accountant'}),
            'sport_position':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. GK, ST, CB'}),
            'jersey_number':     forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '99'}),
            'photo':             forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'id_document':       forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'payslip':           forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'appointment_letter': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
        }
        labels = {
            'first_name':        'First Name *',
            'last_name':         'Last Name *',
            'date_of_birth':     'Date of Birth *',
            'national_id_number': 'National ID Number *',
            'kra_pin':           'KRA PIN *',
            'phone':             'Phone Number *',
            'department':        'County Department',
            'employee_number':   'Employee/Payroll Number',
            'position_title':    'Job Title / Designation',
            'sport_position':    'Playing Position',
            'jersey_number':     'Jersey Number',
            'photo':             'Passport Photo *',
            'id_document':       'Copy of National ID *',
            'payslip':           'Latest Payslip * (proof of employment)',
            'appointment_letter': 'Appointment Letter (optional)',
        }

    def clean_phone(self):
        return validate_kenya_phone(self.cleaned_data.get('phone', ''))

    def clean_kra_pin(self):
        pin = self.cleaned_data.get('kra_pin', '').strip().upper()
        if pin and (len(pin) != 11 or not pin[0].isalpha() or
                    not pin[1:10].isdigit() or not pin[10].isalpha()):
            raise forms.ValidationError(
                'KRA PIN must be 11 characters (e.g. A001234567B).'
            )
        return pin
