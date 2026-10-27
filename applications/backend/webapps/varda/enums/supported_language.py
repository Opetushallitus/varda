import enum


class SupportedLanguage(enum.Enum):
    FI = "FI"
    SV = "SV"

    @classmethod
    def list(cls):
        return [supported_language.value for supported_language in cls]
