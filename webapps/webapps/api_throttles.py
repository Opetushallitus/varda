from rest_framework.throttling import UserRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'


class SustainedGetRateThrottle(UserRateThrottle):
    scope = 'sustained_get'


class SustainedModifyRateThrottle(UserRateThrottle):
    scope = 'sustained_modify'


class BurstRateThrottleStrict(UserRateThrottle):
    scope = 'burst_strict'


class SustainedRateThrottleStrict(UserRateThrottle):
    scope = 'sustained_strict'
