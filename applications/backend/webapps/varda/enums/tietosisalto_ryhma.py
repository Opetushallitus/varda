import enum


class TietosisaltoRyhma(enum.Enum):
    """
    Vakajarjestaja integraatio_organisaatio fields.
    Note: This enum is not used in model choises so altering existing fields need manual work. Adding new ones not.
    """

    VAKATIEDOT = "vakatiedot"
    TYONTEKIJATIEDOT = "tyontekijatiedot"
    TAYDENNYSKOULUTUSTIEDOT = "taydennyskoulutustiedot"
    VUOKRATTUHENKILOSTOTIEDOT = "vuokrattuhenkilostotiedot"
    TUKIPAATOSTIEDOT = "tukipaatostiedot"
    TOIMIJATIEDOT = "toimijatiedot"
    RAPORTIT = "raportit"

    def __str__(self):
        if not isinstance(self.value, str):
            return str(self.value)

        return self.value
