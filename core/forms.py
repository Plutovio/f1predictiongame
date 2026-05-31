"""
F1 Predictor — Forms
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from core.models import UserProfile, Team


class SignUpForm(UserCreationForm):
    """User registration form."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all',
            'placeholder': 'Email address',
        })
    )
    favorite_team = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='Select your team (optional)',
        widget=forms.Select(attrs={
            'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all'
        self.fields['username'].widget.attrs.update({
            'class': input_class,
            'placeholder': 'Username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': input_class,
            'placeholder': 'Password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': input_class,
            'placeholder': 'Confirm password',
        })

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # Update profile with favorite team
            favorite_team = self.cleaned_data.get('favorite_team')
            if favorite_team:
                profile = user.profile
                profile.favorite_team = favorite_team
                profile.save()
        return user


class LoginForm(forms.Form):
    """User login form."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all',
            'placeholder': 'Password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/20 bg-white/5 text-red-500 focus:ring-red-500',
        })
    )


class ProfileEditForm(forms.ModelForm):
    """Profile editing form."""
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 transition-all',
            'placeholder': 'First name',
        })
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 transition-all',
            'placeholder': 'Last name',
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 transition-all',
            'placeholder': 'Email',
        })
    )

    class Meta:
        model = UserProfile
        fields = ('bio', 'favorite_team', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 transition-all',
                'placeholder': 'Tell us about yourself...',
                'rows': 3,
            }),
            'favorite_team': forms.Select(attrs={
                'class': 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-red-500 transition-all',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'w-full text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:bg-red-600 file:text-white hover:file:bg-red-700 file:cursor-pointer',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
