from .models import PageView
from django.utils.deprecation import MiddlewareMixin

class PageViewMiddleware(MiddlewareMixin):
    TARGET_NAMES = {'user_form'} # tên urlpattern cần log (form landing)
    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            # chỉ log GET
            if request.method != 'GET':
                return
            resolver_match = request.resolver_match
            if not resolver_match:
                return
            if resolver_match.url_name not in self.TARGET_NAMES:
                return
            ip = (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "").split(",")[0].strip()
            ua = request.META.get("HTTP_USER_AGENT", "")
            if not request.session.session_key:
                request.session.save() # đảm bảo có session_key
            
            PageView.objects.create(
                path=request.path,
                session_key=request.session.session_key,
                ip=ip or None,
                user_agent=ua[:500],
            )

        except Exception as e:
            raise e