from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password as django_validate_pw
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name', read_only=True)
    lastName = serializers.CharField(source='last_name', read_only=True)
    avatarUrl = serializers.SerializerMethodField()
    kycStatus = serializers.CharField(source='kyc_status', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'firstName', 'lastName', 'phone',
            'avatarUrl', 'locale', 'roles', 'kycStatus', 'createdAt',
        ]

    def get_avatarUrl(self, obj):
        return obj.avatar_url or None


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=25, required=False, allow_blank=True, default='')

    def validate_email(self, value: str) -> str:
        value = value.lower().strip()
        # Only block if a non-deleted account exists with this email.
        # Soft-deleted accounts (deleted_at__isnull=False) are purged on new signup.
        if User.objects.filter(email=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_phone(self, value: str):
        if value and User.objects.filter(phone=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('An account with this phone number already exists.')
        return value or None

    def validate_password(self, value: str) -> str:
        try:
            django_validate_pw(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class HostSignupSerializer(serializers.Serializer):
    """Host signup allows existing emails (for guest→host conversion)."""
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=25, required=False, allow_blank=True, default='')

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

    def validate_phone(self, value: str):
        return value or None

    def validate_password(self, value: str) -> str:
        try:
            django_validate_pw(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class UpdateProfileSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name', max_length=100, required=False)
    lastName = serializers.CharField(source='last_name', max_length=100, required=False)

    class Meta:
        model = User
        fields = ['firstName', 'lastName', 'phone', 'locale']

    def validate_phone(self, value: str):
        if not value:
            return None
        if User.objects.exclude(pk=self.instance.pk).filter(phone=value).exists():
            raise serializers.ValidationError('This phone number is already in use.')
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value: str) -> str:
        try:
            django_validate_pw(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
