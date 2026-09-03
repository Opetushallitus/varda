from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = "burst"


class SustainedGetRateThrottle(UserRateThrottle):
    scope = "sustained_get"


class SustainedModifyRateThrottle(UserRateThrottle):
    scope = "sustained_modify"


class PublicAnonThrottle(AnonRateThrottle):
    scope = "public"
