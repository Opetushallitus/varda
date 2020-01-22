import enum


class Lahdejarjestelma(enum.Enum):
    """
    Used in model so changes require makemigration
    """
    VARDA = 'VARDA'
    ORGANISAATIO = 'ORGANISAATIOPALVELU'

    def __str__(self):
        if not isinstance(self.name, str):
            return str(self.name)

        return self.name

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)
