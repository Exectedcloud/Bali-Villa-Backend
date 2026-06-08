from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from .models import HostProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'roles',
        'email_verified', 'is_active', 'is_staff', 'created_at', 'is_deleted',
    )
    list_filter = ('kyc_status', 'is_staff', 'is_active', 'locale', 'email_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['soft_delete_users', 'restore_users', 'mark_email_verified']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name', 'phone', 'avatar_url', 'locale')}),
        ('Roles & KYC', {'fields': ('roles', 'kyc_status', 'wechat_openid')}),
        ('Email verification', {'fields': ('email_verified', 'email_verification_token')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'deleted_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'roles'),
        }),
    )

    @admin.display(boolean=True, description='Deleted')
    def is_deleted(self, obj):
        return obj.deleted_at is not None

    # ── hard delete (the default Delete button) ───────────────────────────────

    def delete_model(self, request, obj):
        """Hard delete. If the user has protected records (bookings, reviews),
        show an error rather than silently failing."""
        try:
            obj.delete()
        except ProtectedError as e:
            protected = ', '.join(
                f'{r.__class__.__name__} #{r.pk}' for r in list(e.protected_objects)[:5]
            )
            self.message_user(
                request,
                f'Cannot delete {obj.email} — they have linked records that must be '
                f'removed first ({protected}…). Use "Soft-delete" instead to disable '
                f'the account without removing data.',
                level='error',
            )

    def delete_queryset(self, request, queryset):
        """Bulk hard delete. Skips users with protected records and reports them."""
        deleted, failed = 0, []
        for user in queryset:
            try:
                user.delete()
                deleted += 1
            except ProtectedError:
                failed.append(user.email)
        if deleted:
            self.message_user(request, f'{deleted} user(s) permanently deleted.')
        if failed:
            self.message_user(
                request,
                f'Could not delete {len(failed)} user(s) with linked records: {", ".join(failed)}.',
                level='warning',
            )

    # ── admin actions ─────────────────────────────────────────────────────────

    @admin.action(description='Soft-delete selected users (disable, keep data)')
    def soft_delete_users(self, request, queryset):
        updated = queryset.update(deleted_at=timezone.now(), is_active=False)
        self.message_user(request, f'{updated} user(s) soft-deleted (account disabled, data kept).')

    @admin.action(description='Restore selected users (undo soft-delete)')
    def restore_users(self, request, queryset):
        updated = queryset.update(deleted_at=None, is_active=True)
        self.message_user(request, f'{updated} user(s) restored.')

    @admin.action(description='Mark email as verified')
    def mark_email_verified(self, request, queryset):
        updated = queryset.update(email_verified=True, email_verification_token=None)
        self.message_user(request, f'{updated} user(s) marked as email-verified.')


@admin.register(HostProfile)
class HostProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'kyc_status', 'is_verified', 'response_rate', 'hosting_since')
    list_filter = ('kyc_status', 'is_verified')
    search_fields = ('display_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'total_revenue_idr', 'avg_rating', 'total_bookings')
    actions = ['approve_kyc']

    @admin.action(description='Approve KYC for selected hosts')
    def approve_kyc(self, request, queryset):
        updated = queryset.update(kyc_status=HostProfile.KYC_APPROVED, is_verified=True)
        self.message_user(request, f'{updated} host(s) KYC approved.')
