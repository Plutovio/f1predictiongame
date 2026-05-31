"""
F1 Predictor — Authentication Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.forms import SignUpForm, LoginForm, ProfileEditForm


def signup_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to F1 Predictor, {user.username}! 🏎️')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors in the signup form.')
    else:
        form = SignUpForm()

    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember = form.cleaned_data.get('remember_me', False)

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if not remember:
                    request.session.set_expiry(0)  # Session expires on browser close
                messages.success(request, f'Welcome back, {user.username}!')
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors in the login form.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """User logout."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def profile_view(request):
    """User profile page."""
    from core.models import PredictionScore, Prediction
    from django.db.models import Sum, Count, Q, Avg

    season = 2026
    profile = request.user.profile

    # Stats
    scores = PredictionScore.objects.filter(user=request.user, race__season=season)
    stats = {
        'total_points': scores.aggregate(t=Sum('total_points'))['t'] or 0,
        'predictions': Prediction.objects.filter(user=request.user, race__season=season).count(),
        'accuracy': profile.accuracy_percentage(),
        'exact_podiums': scores.filter(exact_podium_bonus=True).count(),
        'streak': profile.current_streak(),
        'avg_points': round(scores.aggregate(a=Avg('total_points'))['a'] or 0, 1),
    }

    # Recent predictions
    recent = Prediction.objects.filter(
        user=request.user, race__season=season
    ).select_related('race', 'p1_driver', 'p2_driver', 'p3_driver').order_by(
        '-race__round_number'
    )[:10]

    # Attach scores to predictions
    for pred in recent:
        try:
            pred.score_obj = pred.score
        except PredictionScore.DoesNotExist:
            pred.score_obj = None

    context = {
        'profile': profile,
        'stats': stats,
        'recent_predictions': recent,
    }
    return render(request, 'auth/profile.html', context)


@login_required
def profile_edit_view(request):
    """Edit user profile."""
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            # Update user fields
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save()

            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=profile, user=request.user)

    return render(request, 'auth/profile_edit.html', {'form': form})
