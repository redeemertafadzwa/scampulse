from rest_framework.throttling import SimpleRateThrottle


class DeviceRateThrottle(SimpleRateThrottle):
    """Throttle per anonymous device token (X-Device-Token header)."""
    scope = "device"

    def get_cache_key(self, request, view):
        token = request.headers.get("X-Device-Token", "")
        if not token:
            return None  # fall back to anon/IP throttle
        return self.cache_format % {"scope": self.scope, "ident": token[:64]}
