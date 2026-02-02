import enum


class EnvironmentType(enum.Enum):
    ANONYMIZATION = "env-varda-anonymization"
    PROD = "env-varda-prod"
    TESTING = "env-varda-testing"
