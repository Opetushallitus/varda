import enum


class AikaleimaAvain(enum.Enum):
    """
    Used in model so changes in values require makemigration
    """
    AUDIT_LOG_AWS_LAST_UPDATE = 'AUDIT_LOG_AWS_LAST_UPDATE'
    HENKILOMUUTOS_LAST_UPDATE = 'HENKILOMUUTOS_LAST_UPDATE'
    HUOLTAJASUHDEMUUTOS_LAST_UPDATE = 'HUOLTAJASUHDEMUUTOS_LAST_UPDATE'
    ORGANISAATIOS_LAST_UPDATE = 'ORGANISAATIOS_LAST_UPDATE'
    ORGANISAATIOS_VARDA_LAST_UPDATE = 'ORGANISAATIOS_VARDA_LAST_UPDATE'
    REQUEST_SUMMARY_LAST_UPDATE = 'REQUEST_SUMMARY_LAST_UPDATE'

    def __str__(self):
        if not isinstance(self.name, str):
            return str(self.name)

        return self.name

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)
