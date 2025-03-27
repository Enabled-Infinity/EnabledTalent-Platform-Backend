from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from .models import CandidateProfile, CandidateConvo, CandidatePrompt
from users.models import User
from unittest.mock import patch, MagicMock

class CandidateConvoTests(APITestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testjobseeker',
            email='seeker@example.com',
            password='testpassword123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create a test conversation
        self.convo = CandidateConvo.objects.create(
            user=self.user,
            title="Test Job Search"
        )
        
    def test_list_conversations(self):
        """Test that a user can list their conversations"""
        url = reverse('candidate-conversations-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_create_conversation(self):
        """Test that a user can create a new conversation"""
        url = reverse('candidate-conversations-list')
        data = {'title': 'New Job Search'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CandidateConvo.objects.count(), 2)
        
    @patch('candidates.models.query_jobs')
    @patch('candidates.models.client')
    def test_create_prompt(self, mock_client, mock_query_jobs):
        """Test that a user can create a new prompt in a conversation"""
        # Mock the OpenAI responses
        mock_query_jobs.return_value = ["Sample job results"]
        
        # Mock the thread creation
        mock_thread = MagicMock()
        mock_thread.id = "thread_12345"
        mock_client.beta.threads.create.return_value = mock_thread
        
        # Mock the message responses
        mock_message = MagicMock()
        mock_client.beta.threads.messages.create.return_value = mock_message
        
        # Mock the stream run
        mock_run = MagicMock()
        mock_client.beta.threads.runs.stream.return_value.__enter__.return_value = mock_run
        
        # Mock the messages list
        mock_messages_list = MagicMock()
        mock_message_content = MagicMock()
        mock_message_content.text.value = "This is a test response"
        mock_messages_data = MagicMock()
        mock_messages_data.content = [mock_message_content]
        mock_messages_list.data = [mock_messages_data]
        mock_client.beta.threads.messages.list.return_value = mock_messages_list
        
        # Set user channel name (required by the view)
        self.user.ws_channel_name = "test_channel"
        self.user.save()
        
        # Create a prompt
        url = reverse('candidate-prompts', kwargs={'pk': self.convo.id})
        data = {'text_query': 'Looking for Python developer jobs'}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CandidatePrompt.objects.count(), 1)
        self.assertEqual(CandidatePrompt.objects.first().text_query, 'Looking for Python developer jobs')
        self.assertEqual(CandidatePrompt.objects.first().response_text, 'This is a test response')
        
    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access conversations"""
        # Log out
        self.client.logout()
        
        url = reverse('candidate-conversations-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
