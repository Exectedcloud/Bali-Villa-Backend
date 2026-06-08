from django.core.management.base import BaseCommand
from services.translation import translate
from villas.models import Villa
from reviews.models import Review


class Command(BaseCommand):
    help = 'Fill missing translations for all villas and reviews in the database.'

    def handle(self, *args, **options):
        self._translate_villas()
        self._translate_reviews()

    def _translate_villas(self):
        villas = Villa.objects.all()
        updated = 0
        for villa in villas:
            changed = []
            if villa.title_en and not villa.title_zh:
                villa.title_zh = translate(villa.title_en, 'ZH', 'EN')
                changed.append('title_zh')
            elif villa.title_zh and not villa.title_en:
                villa.title_en = translate(villa.title_zh, 'EN-US', 'ZH')
                changed.append('title_en')
            if villa.description_en and not villa.description_zh:
                villa.description_zh = translate(villa.description_en, 'ZH', 'EN')
                changed.append('description_zh')
            elif villa.description_zh and not villa.description_en:
                villa.description_en = translate(villa.description_zh, 'EN-US', 'ZH')
                changed.append('description_en')
            if changed:
                villa.save(update_fields=changed)
                updated += 1
                self.stdout.write(f'  Villa {villa.id} ({villa.slug}): filled {changed}')
        self.stdout.write(self.style.SUCCESS(f'Villas: {updated}/{villas.count()} updated.'))

    def _translate_reviews(self):
        reviews = Review.objects.filter(text_translated='')
        updated = 0
        for review in reviews:
            lang = review.text_original_lang
            target_lang = 'EN-US' if lang == 'zh' else 'ZH'
            translated_lang = 'en' if lang == 'zh' else 'zh'
            review.text_translated = translate(review.text_original, target_lang)
            review.text_translated_lang = translated_lang
            review.save(update_fields=['text_translated', 'text_translated_lang'])
            updated += 1
            self.stdout.write(f'  Review {review.id}: translated to {translated_lang}')
        self.stdout.write(self.style.SUCCESS(f'Reviews: {updated} updated.'))
