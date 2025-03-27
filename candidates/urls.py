from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import CandidateViewSet,NoteViewSet,PromptAPI, CandidateConvoViewSet, CandidatePromptViewSet

router = DefaultRouter()
router.register(r'conversations', CandidateConvoViewSet, basename='candidate-conversations')
router.register(r'', CandidateViewSet, basename='candidate')
router.register(r'note', NoteViewSet, basename='note')

urlpatterns = [
    path('prompt/', PromptAPI.as_view()),
    path('conversations/<int:pk>/prompts/', CandidatePromptViewSet.as_view({'get': 'list', 'post': 'create'}), name='candidate-prompts'),
    path('conversations/<int:pk>/prompts/<int:id>/', CandidatePromptViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='candidate-prompt-detail'),
    path('conversations/<int:pk>/prompts/<int:id>/follow-up-suggestions/', 
         CandidatePromptViewSet.as_view({'post': 'get_follow_up_job_suggestions'}), 
         name='candidate-prompt-suggestions'),
]
urlpatterns += router.urls