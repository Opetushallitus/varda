import enum


class Yhteystietoryhmatyyppi(enum.Enum):
    TYOOSOITE = 'yhteystietotyyppi2'
    VTJ_VAKINAINEN_KOTIMAINEN_OSOITE = 'yhteystietotyyppi4'

    def __str__(self):
        return self.value


class YhteystietoAlkupera(enum.Enum):
    VTJ = 'alkupera1'

    def __str__(self):
        return self.value


class YhteystietoTyyppi(enum.Enum):
    YHTEYSTIETO_KATUOSOITE = 'YHTEYSTIETO_KATUOSOITE'
    YHTEYSTIETO_POSTINUMERO = 'YHTEYSTIETO_POSTINUMERO'
    YHTEYSTIETO_KAUPUNKI = 'YHTEYSTIETO_KAUPUNKI'

    def __str__(self):
        return self.value
