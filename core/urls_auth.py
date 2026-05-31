"""
F1 Predictor — Authentication URL Configuration
"""
from django.urls import path
from core.views.auth import login_view, signup_view, logout_view, profile_view, profile_edit_view

urlpatterns = [
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),
]
