import ipaddress

from core.models import SiteVisit


class SiteVisitTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _extract_valid_ip(self, request):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        candidates = []
        if forwarded_for:
            candidates.extend([part.strip() for part in forwarded_for.split(',') if part.strip()])
        remote_addr = request.META.get('REMOTE_ADDR')
        if remote_addr:
            candidates.append(remote_addr.strip())

        for raw_ip in candidates:
            try:
                return str(ipaddress.ip_address(raw_ip))
            except ValueError:
                continue
        return None

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith('/static/') or request.path.startswith('/admin/jsi18n/'):
            return response

        try:
            session_key = getattr(request.session, 'session_key', None)
        except Exception:
            session_key = None

        try:
            SiteVisit.objects.create(
                path=request.path[:255],
                session_key=session_key,
                ip_address=self._extract_valid_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception:
            # Analytics must never break core user flow.
            pass

        return response
