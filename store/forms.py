import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import Order


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email address")

    error_messages = {
        **UserCreationForm.error_messages,
        "password_mismatch": "The passwords do not match. Please try again.",
    }

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email


class CheckoutForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=16,
        label="Phone number",
        validators=[
            RegexValidator(
                regex=re.compile(r"^\+?[0-9]{10,15}$"),
                message="Enter a valid phone number with 10 to 15 digits.",
            )
        ],
        widget=forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "9876543210"}),
    )
    postal_code = forms.CharField(
        max_length=6,
        label="PIN code",
        validators=[
            RegexValidator(
                regex=r"^[0-9]{6}$",
                message="Enter a valid 6-digit Indian PIN code.",
            )
        ],
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "postal-code"}),
    )

    class Meta:
        model = Order
        fields = ("full_name", "phone", "address_line", "city", "state", "postal_code")
        labels = {
            "full_name": "Full name",
            "address_line": "Street address",
            "city": "City",
            "state": "State",
        }
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "address_line": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2"}),
            "state": forms.TextInput(attrs={"autocomplete": "address-level1"}),
        }
