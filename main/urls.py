from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    JobPostViewSet,
    AgentAPI
)

router = DefaultRouter()
router.register(r'jobpost', JobPostViewSet, basename="jobpost")

urlpatterns = [
    path('agent/', AgentAPI.as_view(), name='agent-search')
]
urlpatterns += router.urls