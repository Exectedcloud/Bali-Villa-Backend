import logging
import secrets

from django.conf import settings

logger = logging.getLogger(__name__)
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from services.email import send_verification_email, send_password_reset_email

from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    UpdateProfileSerializer,
    UserSerializer,
)

User = get_user_model()

# ─── cookie helpers ───────────────────────────────────────────────────────────

def _set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    jwt = settings.SIMPLE_JWT
    secure = jwt.get('AUTH_COOKIE_SECURE', False)
    httponly = jwt.get('AUTH_COOKIE_HTTP_ONLY', True)
    samesite = jwt.get('AUTH_COOKIE_SAMESITE', 'Lax')
    response.set_cookie(
        jwt['AUTH_COOKIE'],
        access_token,
        max_age=int(jwt['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        httponly=httponly,
        secure=secure,
        samesite=samesite,
    )
    response.set_cookie(
        jwt['AUTH_COOKIE_REFRESH'],
        refresh_token,
        max_age=int(jwt['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        httponly=httponly,
        secure=secure,
        samesite=samesite,
    )


def _delete_auth_cookies(response) -> None:
    jwt = settings.SIMPLE_JWT
    samesite = jwt.get('AUTH_COOKIE_SAMESITE', 'Lax')
    response.delete_cookie(jwt['AUTH_COOKIE'], samesite=samesite)
    response.delete_cookie(jwt['AUTH_COOKIE_REFRESH'], samesite=samesite)


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


# ─── auth views ───────────────────────────────────────────────────────────────

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        # Remove any soft-deleted record with this email so the new account
        # gets a clean slot (avoids UNIQUE constraint on email).
        User.objects.filter(email=d['email'], deleted_at__isnull=False).delete()

        user = User.objects.create_user(
            email=d['email'],
            password=d['password'],
            first_name=d['firstName'],
            last_name=d['lastName'],
            phone=d.get('phone') or None,
            roles=['guest'],
            email_verified=False,
        )
        user.email_verification_token = secrets.token_urlsafe(32)
        user.save(update_fields=['email_verification_token'])
        try:
            send_verification_email(user)
        except Exception:
            logger.exception('Failed to send verification email to %s', user.email)

        resp = {'detail': 'Please check your email to verify your account.'}
        if settings.DEBUG:
            verify_url = f"{settings.FRONTEND_URL}/verify-email?uid={user.id}&token={user.email_verification_token}"
            resp['debug_verify_url'] = verify_url
        return Response(resp, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {'error': 'This account has been deactivated.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user.email_verified:
            return Response(
                {'error': 'Please verify your email before logging in. Check your inbox for the verification link.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        access, refresh = _tokens_for_user(user)
        response = Response({'user': UserSerializer(user).data})
        _set_auth_cookies(response, access, refresh)
        return response


class LogoutView(APIView):
    def post(self, request):
        response = Response({'detail': 'Logged out.'})
        _delete_auth_cookies(response)
        return response


class MeView(APIView):
    def get(self, request):
        return Response({'user': UserSerializer(request.user).data})

    def patch(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'user': UserSerializer(request.user).data})


class TokenRefreshView(APIView):
    """Reads refresh token from cookie, issues a new access token."""
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH'))
        if not raw_refresh:
            return Response({'error': 'No refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw_refresh)
            access = str(refresh.access_token)
        except TokenError:
            return Response(
                {'error': 'Refresh token is invalid or expired. Please log in again.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        response = Response({'detail': 'Token refreshed.'})
        _set_auth_cookies(response, access, raw_refresh)
        return response


# ─── password reset ───────────────────────────────────────────────────────────

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        debug_url = None
        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            base_url = settings.HOST_URL if 'host' in (user.roles or []) else settings.FRONTEND_URL
            send_password_reset_email(user, uid, token, base_url=base_url)
            if settings.DEBUG:
                debug_url = f"{base_url}/reset-password?uid={uid}&token={token}"
        except User.DoesNotExist:
            pass  # don't reveal whether the email exists

        resp = {'detail': 'If that email is registered, a reset link has been sent.'}
        if settings.DEBUG and debug_url:
            resp['debug_reset_url'] = debug_url
        return Response(resp)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            pk = force_str(urlsafe_base64_decode(d['uid']))
            user = User.objects.get(pk=pk)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, d['token']):
            return Response(
                {'error': 'This reset link has expired or already been used.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(d['new_password'])
        user.save()

        # Clear any active session cookies so the user must log in with the new password
        response = Response({'detail': 'Password updated successfully.'})
        _delete_auth_cookies(response)
        return response


# ─── not-yet-implemented stubs ────────────────────────────────────────────────

class LoginPhoneView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {'error': 'Phone + OTP login is not yet implemented.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class LoginWechatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {'error': 'WeChat OAuth login is not yet implemented.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class OtpRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {'error': 'SMS OTP is not yet implemented.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


# ─── email verification ───────────────────────────────────────────────────────

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token', '')

        if not uid or not token:
            return Response(
                {'error': 'uid and token are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {'error': 'Invalid or expired verification link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stored = user.email_verification_token or ''
        if not stored or not secrets.compare_digest(stored, token):
            return Response(
                {'error': 'Invalid or expired verification link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email_verified = True
        user.email_verification_token = None
        user.save(update_fields=['email_verified', 'email_verification_token'])

        return Response({'detail': 'Email verified successfully. You can now log in.'})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').lower().strip()
        debug_url = None
        try:
            user = User.objects.get(email=email)
            if not user.email_verified:
                user.email_verification_token = secrets.token_urlsafe(32)
                user.save(update_fields=['email_verification_token'])
                base_url = settings.HOST_URL if 'host' in (user.roles or []) else settings.FRONTEND_URL
                send_verification_email(user, base_url=base_url)
                if settings.DEBUG:
                    debug_url = f"{base_url}/verify-email?uid={user.id}&token={user.email_verification_token}"
        except User.DoesNotExist:
            pass  # don't reveal whether the email exists

        resp = {'detail': 'If that email is registered and unverified, a new link has been sent.'}
        if settings.DEBUG and debug_url:
            resp['debug_verify_url'] = debug_url
        return Response(resp)


# ─── profile / password ───────────────────────────────────────────────────────

class ChangePasswordView(APIView):
    def post(self, request):
        old_password = request.data.get('oldPassword')
        new_password = request.data.get('newPassword')

        if not old_password or not new_password:
            return Response(
                {'error': 'oldPassword and newPassword are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, request.user)
        except ValidationError as e:
            return Response({'error': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])

        # Re-issue tokens so the session stays alive after the password change
        access, refresh = _tokens_for_user(request.user)
        response = Response({'detail': 'Password changed successfully.'})
        _set_auth_cookies(response, access, refresh)
        return response
