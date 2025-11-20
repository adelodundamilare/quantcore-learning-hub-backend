from app.services.user import user_service
from app.services.school import school_service
from app.services.course import course_service
from app.services.trading import trading_service
from app.services.notification import notification_service
from app.services.exam import exam_service
from app.services.report import report_service
from app.services.permission import permission_service
from app.services.logo import logo_service
from app.services.course_progress import course_progress_service
from app.services.popular_stocks_cache import popular_stocks_cache

class ServiceRegistry:
    @property
    def user(self):
        return user_service
    @property
    def school(self):
        return school_service
    @property
    def course(self):
        return course_service
    @property
    def trading(self):
        return trading_service
    @property
    def notification(self):
        return notification_service
    @property
    def exam(self):
        return exam_service
    @property
    def report(self):
        return report_service
    @property
    def permission(self):
        return permission_service
    @property
    def logo(self):
        return logo_service
    @property
    def lesson_progress(self):
        return course_progress_service
    @property
    def popular_stocks(self):
        return popular_stocks_cache

services = ServiceRegistry()