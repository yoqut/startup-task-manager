import json
import os
from typing import Any, Dict, Optional


class I18nEngine:

    def __init__(
        self,
        translations_path: str = "locales",
        default_lang: str = "uz",
        db=None,
        cache=None
    ):
        self.path = translations_path
        self.default_lang = default_lang

        self.db = db          # async DB (optional)
        self.cache = cache    # redis (optional)

        self.translations = self._load()

        self.fallback_chain = ["uz", "ru", "en"]

    # ─────────────────────────────
    # LOAD FILES
    # ─────────────────────────────

    def _load(self) -> Dict[str, dict]:
        data = {}

        if not os.path.exists(self.path):
            return data

        for f in os.listdir(self.path):
            if f.endswith(".json"):
                lang = f.replace(".json", "")

                try:
                    with open(os.path.join(self.path, f), "r", encoding="utf-8") as file:
                        data[lang] = json.load(file)
                except:
                    pass

        return data

    # ─────────────────────────────
    # DB LANG
    # ─────────────────────────────

    def get_user_lang(self, user_id: int) -> str:

        if self.cache:
            cached = self.cache.get(f"lang:{user_id}")
            if cached:
                return cached

        if self.db:
            user = self.db.users.get(id=user_id)
            if user and user.lang:
                lang = user.lang

                if self.cache:
                    self.cache.set(f"lang:{user_id}", lang)

                return lang

        return self.default_lang

    # ─────────────────────────────
    # CORE TRANSLATE
    # ─────────────────────────────

    def _resolve(self, lang: str, key: str) -> Optional[str]:

        for l in [lang] + self.fallback_chain:

            if l in self.translations and key in self.translations[l]:
                return self.translations[l][key]

        return None

    def gettext(self, lang: str, key: str, **kwargs) -> str:

        text = self._resolve(lang, key) or key

        return text.format(**kwargs)

    # ─────────────────────────────
    # PLURAL SUPPORT
    # ─────────────────────────────

    def ngettext(self, lang: str, key: str, count: int, **kwargs) -> str:

        raw = self._resolve(lang, key)

        if not raw:
            return key

        forms = raw.split("|")  # "one|many"

        if count == 1:
            text = forms[0]
        else:
            text = forms[1] if len(forms) > 1 else forms[0]

        return text.format(count=count, **kwargs)

    # ─────────────────────────────
    # INLINE KEYBOARD SUPPORT
    # ─────────────────────────────

    def translate_kb(self, lang: str, keyboard: list[list[str]]) -> list[list[str]]:

        return [
            [self.gettext(lang, btn) for btn in row]
            for row in keyboard
        ]