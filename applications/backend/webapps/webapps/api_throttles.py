from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = "burst"


class SustainedGetRateThrottle(UserRateThrottle):
    scope = "sustained_get"


class SustainedModifyRateThrottle(UserRateThrottle):
    scope = "sustained_modify"


class PublicAnonThrottle(AnonRateThrottle):
    scope = "public"
