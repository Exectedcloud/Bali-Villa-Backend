from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'villa', 'guest', 'rating', 'text_original_lang', 'is_visible', 'published_at')
    list_filter = ('is_visible', 'text_original_lang')
    search_fields = ('villa__slug', 'guest__email', 'text_original')
    readonly_fields = ('published_at', 'updated_at', 'flagged_at')
    actions = ['hide_reviews', 'unhide_reviews']

    @admin.action(description='Hide selected reviews')
    def hide_reviews(self, request, queryset):
        updated = queryset.update(is_visible=False)
        self.message_user(request, f'{updated} review(s) hidden.')

    @admin.action(description='Unhide selected reviews')
    def unhide_reviews(self, request, queryset):
        updated = queryset.update(is_visible=True)
        self.message_user(request, f'{updated} review(s) made visible.')
