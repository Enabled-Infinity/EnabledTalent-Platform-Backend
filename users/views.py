from rest_framework.views import APIView,Http404
from rest_framework import permissions,status,viewsets
from rest_framework.response import Response
from django.contrib.auth import logout,login,authenticate,update_session_auth_hash
from users.models import User
from rest_framework.decorators import action
# Create your views here.
from . import serializers,permissions as  pp
from organization.models import OrganizationInvite


class SignupView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        # Check if invite code is provided
        invite_code = request.data.get("invite_code")
        if invite_code:
            try:
                invite = OrganizationInvite.objects.get(invite_code=invite_code)
            except OrganizationInvite.DoesNotExist:
                return Response({"detail": "Invalid invite code."}, status=status.HTTP_404_NOT_FOUND)

        # Validate and create user
        serializer = serializers.UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if invite_code:
            # add the user to the organization

            if invite.accepted == False:
                invite.organization.users.add(user)
                invite.accepted=True
                invite.save()
            else:
                print(user)
                user.delete()
                return Response({"detail": "Invite Code already used"}, status=status.HTTP_226_IM_USED)

            
            # Optionally, set the user's subscription type to team member
            # user.subscription_type = 4
            # user.save()

        # Log in the user
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Return the response
        response = Response(status=status.HTTP_201_CREATED)
        response.set_cookie('loggedIn', 'true', httponly=True)      
        return response


class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        login_serializer= serializers.LoginSerializer(
            data=request.data
        )
        login_serializer.is_valid(raise_exception=True)
        user= authenticate(request, **login_serializer.data)

        if user is None:
            response= Response(
                {"detail": "Invalid Credentials"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
            response.set_cookie('loggedIn', 'false', httponly=True)
            return response
        
        if not user.is_active:
            response = Response(
                {"detail": "Account disabled"}, status=status.HTTP_401_UNAUTHORIZED
            )
            response.set_cookie('loggedIn', 'false', httponly=True)
            return response
        
        login(request, user)

        response = Response(status=status.HTTP_200_OK)
        response.set_cookie('loggedIn', 'true', httponly=True, domain="frontend-pulpit.vercel.app")

        return response

class LogoutView(APIView):
    permission_classes= [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)

        response = Response(status=status.HTTP_200_OK)
        response.delete_cookie('loggedIn')
        return response
    
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserSerializer
    permission_classes = (pp.UserViewSetPermissions,)
    queryset = User.objects.all().select_related("profile")

    def list(self, request, *args, **kwargs):
        # dont list all users
        raise Http404
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial",False)
        instance= self.get_object()
        serializer = serializers.UserSerializer(
            instance=instance,data=request.data,partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_200_OK)


         

    @action(methods=("GET",), detail=False, url_path="me")
    def get_current_user_data(self, request):
        return Response(self.get_serializer(request.user).data)

class ChangePasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self,request):
        serializer = serializers.ChangePasswordSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        user= request.user
        if user.check_password(serializer.validated_data.get('current_password')):
            if serializer.validated_data.get('new_password') == serializer.validated_data.get('confirm_new_password'):
                user.set_password(serializer.validated_data.get('new_password'))
                user.save()
                update_session_auth_hash(request, user)
                return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
            return Response({'message':'Password and Confirm Password didnt match'},status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Incorrect old password.'}, status=status.HTTP_400_BAD_REQUEST)



class AddFeedback(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self,request):
        serializer = serializers.FeedbackCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data,status=status.HTTP_201_CREATED)