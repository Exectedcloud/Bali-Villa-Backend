from django.urls import path
from . import views

urlpatterns = [
    # Email/password auth
    path('signup/', views.SignupView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('me/', views.MeView.as_view()),
    path('token/refresh/', views.TokenRefreshView.as_view()),

    # Email verification
    path('verify-email/', views.VerifyEmailView.as_view()),
    path('resend-verification/', views.ResendVerificationView.as_view()),

    # Password reset
    path('password/forgot/', views.ForgotPasswordView.as_view()),
    path('password/reset/', views.ResetPasswordView.as_view()),

    # Stubs — not yet implemented
    path('login/phone/', views.LoginPhoneView.as_view()),
    path('login/wechat/', views.LoginWechatView.as_view()),
    path('otp/request/', views.OtpRequestView.as_view()),
]
