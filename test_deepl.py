import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'balivilla.settings')
django.setup()

import deepl
from django.conf import settings

print(f"DEEPL_API_KEY: {settings.DEEPL_API_KEY}")

try:
    translator = deepl.Translator(settings.DEEPL_API_KEY)
    usage = translator.get_usage()
    print("DeepL connected successfully!")
    print(f"Character usage: {usage.character.count} of {usage.character.limit}")
    
    # Test a translation
    text = "Hello, welcome to Bali!"
    result = translator.translate_text(text, target_lang="ZH")
    print(f"Translation test: '{text}' -> '{result.text}'")
except Exception as e:
    print(f"DeepL translation failed with error: {e}")
    print(f"Error type: {type(e)}")
