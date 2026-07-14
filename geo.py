"""Маппинг Telegram language_code → ISO-код страны + emoji-флаг.

Используем язык аккаунта как прокси для гео. Правило: если код языка
содержит региональную часть (например, 'zh-hans'), берём первые 2 символа.
"""
from __future__ import annotations

UNKNOWN = "XX"

_LANG_TO_COUNTRY: dict[str, str] = {
    "ru": "RU",
    "uk": "UA",
    "be": "BY",
    "kk": "KZ",
    "ky": "KG",
    "uz": "UZ",
    "tg": "TJ",
    "tk": "TM",
    "hy": "AM",
    "az": "AZ",
    "ka": "GE",
    "en": "EN",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "it": "IT",
    "pt": "PT",
    "pl": "PL",
    "cs": "CZ",
    "sk": "SK",
    "sl": "SI",
    "sr": "RS",
    "hr": "HR",
    "bg": "BG",
    "ro": "RO",
    "hu": "HU",
    "el": "GR",
    "nl": "NL",
    "sv": "SE",
    "no": "NO",
    "da": "DK",
    "fi": "FI",
    "et": "EE",
    "lv": "LV",
    "lt": "LT",
    "tr": "TR",
    "ar": "AR",
    "fa": "IR",
    "he": "IL",
    "hi": "IN",
    "ur": "PK",
    "bn": "BD",
    "th": "TH",
    "vi": "VN",
    "id": "ID",
    "ms": "MY",
    "tl": "PH",
    "ja": "JP",
    "ko": "KR",
    "zh": "CN",
}

_COUNTRY_FLAG: dict[str, str] = {
    "RU": "🇷🇺", "UA": "🇺🇦", "BY": "🇧🇾", "KZ": "🇰🇿", "KG": "🇰🇬",
    "UZ": "🇺🇿", "TJ": "🇹🇯", "TM": "🇹🇲", "AM": "🇦🇲", "AZ": "🇦🇿", "GE": "🇬🇪",
    "EN": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷", "ES": "🇪🇸", "IT": "🇮🇹",
    "PT": "🇵🇹", "PL": "🇵🇱", "CZ": "🇨🇿", "SK": "🇸🇰", "SI": "🇸🇮",
    "RS": "🇷🇸", "HR": "🇭🇷", "BG": "🇧🇬", "RO": "🇷🇴", "HU": "🇭🇺",
    "GR": "🇬🇷", "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "DK": "🇩🇰",
    "FI": "🇫🇮", "EE": "🇪🇪", "LV": "🇱🇻", "LT": "🇱🇹", "TR": "🇹🇷",
    "AR": "🌍", "IR": "🇮🇷", "IL": "🇮🇱", "IN": "🇮🇳", "PK": "🇵🇰",
    "BD": "🇧🇩", "TH": "🇹🇭", "VN": "🇻🇳", "ID": "🇮🇩", "MY": "🇲🇾",
    "PH": "🇵🇭", "JP": "🇯🇵", "KR": "🇰🇷", "CN": "🇨🇳",
    UNKNOWN: "🌐",
}


def language_code_to_geo(language_code: str | None) -> str:
    if not language_code:
        return UNKNOWN
    base = language_code.lower().split("-")[0]
    return _LANG_TO_COUNTRY.get(base, UNKNOWN)


def flag(geo: str) -> str:
    return _COUNTRY_FLAG.get(geo, "🌐")


def format_geo(geo: str) -> str:
    return f"{flag(geo)} {geo}"


def all_known_geos() -> list[str]:
    seen: list[str] = []
    for c in _LANG_TO_COUNTRY.values():
        if c not in seen:
            seen.append(c)
    seen.append(UNKNOWN)
    return seen
