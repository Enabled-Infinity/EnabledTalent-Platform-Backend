from django.shortcuts import get_object_or_404
from main.models import Channel
from users.models import User

def get_channel(channel_type_num, organization):
    return get_object_or_404(Channel, channel_type=channel_type_num, organization=organization)

# Function to create a new channel object 
def create_channel(channel_type_num, organization):
    try:
        new_channel = Channel.objects.create(
           channel_type=channel_type_num, organization=organization
        )
        return new_channel
    except Exception as e:
        print(str(e), "Error in creating channel object")
        return Channel.objects.get(channel_type=channel_type_num, organization=organization)