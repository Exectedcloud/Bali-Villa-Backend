import logging
import secrets

from django.contrib.auth import get_user_model, authenticate
from django.conf import settings

logger = logging.getLogger(__name__)
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HostProfile
from .permissions import HasHostRole
from .serializers import HostSignupSerializer, LoginSerializer, UserSerializer
from .views import _set_auth_cookies, _tokens_for_user
from services.email import send_verification_email

User = get_user_model()


class HostSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = HostSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        # Check if user with this email already exists
        try:
            user = User.objects.get(email=d['email'])
            # User exists — verify password for security
            if not user.check_password(d['password']):
                return Response(
                    {'error': 'Invalid password for existing account.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            # Already a host — nothing to promote, just direct them to log in
            if 'host' in (user.roles or []):
                return Response(
                    {'error': 'This email is already registered as a host. Please log in.'},
                    status=status.HTTP_409_CONFLICT,
                )
            # Existing guest must have verified email before upgrading to host
            if not user.email_verified:
                return Response(
                    {'error': 'Please verify your email before signing up as a host.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Guest → host promotion (email already verified, issue tokens immediately)
            roles = list(user.roles or [])
            roles.append('host')
            user.roles = roles
            user.save(update_fields=['roles'])
            HostProfile.objects.get_or_create(
                user=user,
                defaults={'display_name': f"{d['firstName']} {d['lastName']}".strip()}
            )
            access, refresh = _tokens_for_user(user)
            response = Response({'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)
            _set_auth_cookies(response, access, refresh)
            return response

        except User.DoesNotExist:
            # Purge any soft-deleted record with this email before creating fresh account
            User.objects.filter(email=d['email'], deleted_at__isnull=False).delete()
            # New user — create with both roles, require email verification
            user = User.objects.create_user(
                email=d['email'],
                password=d['password'],
                first_name=d['firstName'],
                last_name=d['lastName'],
                phone=d.get('phone') or None,
                roles=['guest', 'host'],
                email_verified=False,
            )
            HostProfile.objects.create(
                user=user,
                display_name=f"{d['firstName']} {d['lastName']}".strip(),
            )
            user.email_verification_token = secrets.token_urlsafe(32)
            user.save(update_fields=['email_verification_token'])
            try:
                send_verification_email(user, base_url=settings.HOST_URL)
            except Exception:
                logger.exception('Failed to send verification email to %s', user.email)

            resp = {'detail': 'Please check your email to verify your account.'}
            if settings.DEBUG:
                verify_url = f"{settings.HOST_URL}/verify-email?uid={user.id}&token={user.email_verification_token}"
                resp['debug_verify_url'] = verify_url
            return Response(resp, status=status.HTTP_201_CREATED)


class HostLoginView(APIView):
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
        # Check if user has 'host' role
        if 'host' not in (user.roles or []):
            return Response(
                {'error': 'This account is not registered as a host. Sign up as a host first.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        access, refresh = _tokens_for_user(user)
        response = Response({'user': UserSerializer(user).data})
        _set_auth_cookies(response, access, refresh)
        return response


class HostMeView(APIView):
    permission_classes = [HasHostRole]

    def get(self, request):
        try:
            profile = request.user.host_profile
        except HostProfile.DoesNotExist:
            return Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            'user': UserSerializer(request.user).data,
            'host': {
                'id': profile.id,
                'displayName': profile.display_name,
                'bio': profile.bio,
                'languages': profile.languages,
                'responseRate': int(float(profile.response_rate)),
                'hostingSince': profile.hosting_since,
                'isVerified': profile.is_verified,
                'kycStatus': profile.kyc_status,
                'payoutBank': profile.payout_bank,
                'avgRating': float(profile.avg_rating),
                'totalBookings': profile.total_bookings,
            },
        })
