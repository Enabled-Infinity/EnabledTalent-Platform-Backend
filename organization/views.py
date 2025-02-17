from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import create_organization_invite as create_org_invite
from django.core.mail import send_mail
import os
from .permissions import OrganizationViewSetPermissions

# from . import permissions
from rest_framework import permissions
from .serializers import OrganizationCreateSerializer,OrganizationInviteCreateSerializer,OrganizationSerializer


class OrganizationsViewSet(viewsets.ModelViewSet):
    # permission_classes = (WorkSpaceViewSetPermissions,)
    permission_classes = (permissions.IsAuthenticated, )
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        # All the organizations the request user is a member of
        return self.request.user.organization_set.all()
    #https://xyz.com
    
    

    def create(self, request, *args, **kwargs):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(root_user=self.request.user)

        return Response(self.get_serializer(instance).data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = OrganizationCreateSerializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)

        new_instance = serializer.save()

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(self.get_serializer(new_instance).data)

    @action(methods=("POST",), detail=True, url_path="create-invite")
    def create_organization_invite(self, request, pk):

        #organization = self.get_object().id
        organization= self.get_object()

        invite_code= create_org_invite()
        #email = request.data["email"]  # Assuming email is provided in request data
        
        """
        serializer = WorkSpaceInviteCreateSerializer(data= {
            "workspace": workspace,
            "invite_code": invite_code,
            "email": email
            })
        """

        serializer = OrganizationInviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            organization=organization,
            invite_code=invite_code
            )
        print(os.environ['EMAIL_HOST_USER'])


        # Extract the email address from the validated data and send the email
        recipient_email = serializer.validated_data.get("email")
        print(recipient_email)

        #sending mail
        send_mail(
            'Subject here',
            f'Here is the message. Your code is {invite_code}',
            os.environ['EMAIL_HOST_USER'],  # Sender's email address
            [recipient_email],  # List of recipient email addresses as strings
        )
        
        return Response(serializer.data,status=status.HTTP_201_CREATED)