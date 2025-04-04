from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import CandidateViewSet,NoteViewSet,PromptAPI

router = DefaultRouter()
router.register(r'', CandidateViewSet, basename='candidate')
router.register(r'note', NoteViewSet, basename='note')

urlpatterns = [
    path('prompt/', PromptAPI.as_view())
]
urlpatterns += router.urls