from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from .views import (
    RegistrationFormSchemaAPIView,
    RegisterWelfareMemberAPIView,
    TenantRegistrationView,
    AdminApprovalDashboardView,
    ApproveMemberView,
    MemberPortalDashboardView,
    DownloadReceiptPDFView
)

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='welfare/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login', http_method_names=['get', 'post']), name='logout'),

    # Password Reset Flow (Self-Service Email)
    path('password-reset/',
        auth_views.PasswordResetView.as_view(template_name='welfare/password_reset.html'),
        name='password_reset'),

    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='welfare/password_reset_done.html'),
        name='password_reset_done'),

    path('reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='welfare/password_reset_confirm.html'),
        name='password_reset_confirm'),

    path('reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='welfare/password_reset_complete.html'),
        name='password_reset_complete'),

    # HTML Frontend Form Wizard
    path('register/', TenantRegistrationView.as_view(), name='tenant_register'),
    path('register/success/', TemplateView.as_view(template_name='welfare/success.html'), name='registration_success'),

    # Admin Approval Dashboard
    path('welfare-admin/', AdminApprovalDashboardView.as_view(), name='admin_approval_dashboard'),
    path('welfare-admin/approve/<int:pk>/', ApproveMemberView.as_view(), name='approve_member'),

    # Member Portal Dashboard & PDF Receipts
    path('dashboard/', MemberPortalDashboardView.as_view(), name='member_portal'),
    path('receipt/<str:receipt_no>/pdf/', DownloadReceiptPDFView.as_view(), name='download_receipt_pdf'),

    # REST API Endpoints
    path('api/register/schema/', RegistrationFormSchemaAPIView.as_view(), name='registration_schema_api'),
    path('api/register/', RegisterWelfareMemberAPIView.as_view(), name='registration_submit_api'),
]
