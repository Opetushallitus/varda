import enum


class Lokalisointi(enum.Enum):
    VIRKAILIJA = "lokalisointi_virkailija"
    KANSALAINEN = "lokalisointi_kansalainen"
    JULKINEN = "lokalisointi_julkinen"

    @classmethod
    def list(cls):
        return [lokalisointi.value for lokalisointi in cls]
