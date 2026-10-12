import enum


class BatchErrorType(enum.Enum):
    """
    Note: Used in model so changes in values require makemigration
    """

    LAPSI_HUOLTAJUUSSUHDE_UPDATE = "LAPSI_HUOLTAJUUSSUHDE_UPDATE"
    HENKILOTIETO_UPDATE = "HENKILOTIETO_UPDATE"

    def __str__(self):
        if not isinstance(self.name, str):
            return str(self.name)

        return self.name

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)
