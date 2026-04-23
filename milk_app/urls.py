from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),   # main login page
    path('dashboard/', views.dashboard, name='dashboard'),
    path('scan/', views.scan_qr, name='scan_qr'),
    path('get-farmer/', views.get_farmer, name='get_farmer'),

    path('export-excel/', views.export_excel, name='export_excel'),
    path('monthly-report/', views.monthly_report, name='monthly_report'),
    path('generate-bill/', views.generate_bill, name='generate_bill'),

    # Farmer login system
    path('farmer-login/', views.farmer_login, name='farmer_login'),
    path('farmer-dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('api/farmer-assistant/', views.farmer_assistant_chat, name='farmer_assistant_chat'),
    path('farmer-logout/', views.farmer_logout, name='farmer_logout'),

    # Language switching
    path('change-language/', views.change_language, name='change_language'),

    path('', views.home, name='home'),

    # Password reset
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
]
