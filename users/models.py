from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('roles', ['admin'])
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    KYC_NOT_REQUIRED = 'not_required'
    KYC_PENDING = 'pending'
    KYC_SUBMITTED = 'submitted'
    KYC_APPROVED = 'approved'
    KYC_REJECTED = 'rejected'
    KYC_CHOICES = [
        (KYC_NOT_REQUIRED, 'Not Required'),
        (KYC_PENDING, 'Pending'),
        (KYC_SUBMITTED, 'Submitted'),
        (KYC_APPROVED, 'Approved'),
        (KYC_REJECTED, 'Rejected'),
    ]

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=25, null=True, blank=True, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    locale = models.CharField(
        max_length=5,
        choices=[('zh', 'Chinese'), ('en', 'English')],
        default='zh',
    )
    # e.g. ['guest', 'host', 'admin']
    roles = models.JSONField(default=list)
    wechat_openid = models.CharField(max_length=200, null=True, blank=True, unique=True)
    kyc_status = models.CharField(max_length=20, choices=KYC_CHOICES, default=KYC_NOT_REQUIRED)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Soft-delete: never hard-delete user data
    deleted_at = models.DateTimeField(null=True, blank=True)
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'

    def __str__(self) -> str:
        return self.email


class HostProfile(models.Model):
    KYC_PENDING = 'pending'
    KYC_SUBMITTED = 'submitted'
    KYC_APPROVED = 'approved'
    KYC_REJECTED = 'rejected'
    KYC_CHOICES = [
        (KYC_PENDING, 'Pending'),
        (KYC_SUBMITTED, 'Submitted'),
        (KYC_APPROVED, 'Approved'),
        (KYC_REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='host_profile',
    )
    display_name = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    # e.g. ['Mandarin', 'English', 'Indonesian']
    languages = models.JSONField(default=list)
    response_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    response_time_minutes = models.IntegerField(default=60)
    # year joined as host, e.g. 2019
    hosting_since = models.IntegerField(null=True, blank=True)
    # JSON blob: { bank_name, account_number, account_name }
    payout_bank = models.JSONField(default=dict)
    kyc_status = models.CharField(max_length=20, choices=KYC_CHOICES, default=KYC_PENDING)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    # Denormalised stats refreshed by Celery tasks
    total_revenue_idr = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    total_bookings = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'host_profiles'

    def __str__(self) -> str:
        return self.display_name
