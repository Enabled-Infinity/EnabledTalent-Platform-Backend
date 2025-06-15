from rest_framework.views import APIView,Http404
from rest_framework import permissions,status,viewsets
from rest_framework.response import Response
from django.contrib.auth import logout,login,authenticate,update_session_auth_hash
from users.models import User, EmailVerificationToken
from rest_framework.decorators import action
from django.conf import settings
# from django.core.mail import send_mail
# Create your views here.
from . import serializers,permissions as  pp
from organization.models import OrganizationInvite
import smtplib
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


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
        
        # Create verification token
        verification_token = EmailVerificationToken.objects.create(user=user)
        
        # Send verification email with code
        subjet = "Verify your email address"
        verification_message = f"""
Hello,

Thank you for signing up for EnabledTalent! Please verify your email address to complete your registration.

Your verification code is: {verification_token.code}

If you didn't create an account, you can safely ignore this email.

Best regards,
The HireMod Team
"""
        msg = f"Subject: {subjet}\n\n{verification_message}"
        try:
            print('dedddd')
            smtp =smtplib.SMTP('smtp.elasticemail.com', port='2525')
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM, user.email, msg)
            smtp.quit()
            # send_mail(
            #     subject="Verify your email address",
            #     message=verification_message,
            #     from_email=settings.EMAIL_HOST_USER,
            #     recipient_list=[user.email],
            #     fail_silently=False,
            # )
            print('dede')
        except Exception as e:
            print(f"Failed to send verification email: {str(e)}")
        return Response({
            "detail": "Registration successful! Please check your email for a verification code."
        }, status=status.HTTP_201_CREATED)
    
        """
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
        """



class VerifyEmailView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response({
                "detail": "Email and verification code are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            verification_token = EmailVerificationToken.objects.get(user=user, code=code)
            
            # Check if token is expired
            if verification_token.is_expired:
                # Delete the expired token
                verification_token.delete()
                return Response({
                    "detail": "Verification code has expired. Please request a new one."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark user as verified
            user.is_verified = True
            user.save()
            
            # Delete the token
            verification_token.delete()
            
            # Log the user in
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Return success response
            response = Response({
                "detail": "Email verified successfully."
            }, status=status.HTTP_200_OK)
            
            response.set_cookie('loggedIn', 'true', httponly=True)
            return response
            
        except User.DoesNotExist:
            return Response({
                "detail": "Invalid email address."
            }, status=status.HTTP_400_BAD_REQUEST)
        except EmailVerificationToken.DoesNotExist:
            return Response({
                "detail": "Invalid verification code."
            }, status=status.HTTP_400_BAD_REQUEST)


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
        
        if not user.is_verified:
            # Resend verification email
            verification_token, created = EmailVerificationToken.objects.get_or_create(user=user)
            
            # If token already exists but we're not creating a new one, delete and create fresh
            if not created:
                verification_token.delete()
                verification_token = EmailVerificationToken.objects.create(user=user)
            
            # Send verification email with code
            subjet = "Verify your email address"
            verification_message = f"""
Hello,

Please verify your email address to complete your registration and log in.

Your verification code is: {verification_token.code}

If you didn't create an account, you can safely ignore this email.

Best regards,
The HireMod Team
"""
            msg = f"Subject: {subjet}\n\n{verification_message}"
            smtp =smtplib.SMTP('smtp.elasticemail.com', port='2525')
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM, user.email, msg)
            smtp.quit()
            # send_mail(
            #     subject="Verify your email address",
            #     message=verification_message,
            #     from_email=settings.EMAIL_HOST_USER,
            #     recipient_list=[user.email],
            #     fail_silently=False,
            # )
            
            response = Response(
                {"detail": "Email not verified. A new verification code has been sent to your email."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            response.set_cookie('loggedIn', 'false', httponly=True)
            return response
        
        login(request, user)

        response = Response(status=status.HTTP_200_OK)
        response.set_cookie('loggedIn', 'true', httponly=True)

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
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = User.objects.all().select_related("profile")

    def list(self, request, *args, **kwargs):
        # dont list all users
        raise Http404
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial",False)
        instance= self.get_object()
        
        # Use UserUpdateSerializer for updates that can handle avatar uploads
        serializer = serializers.UserUpdateSerializer(
            instance=instance,data=request.data,partial=partial
        )
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        
        # Return the full user data using the main serializer
        return Response(
            serializers.UserSerializer(updated_instance).data,
            status=status.HTTP_200_OK
        )
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
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



class ResendVerificationEmailView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Check if user is already verified
            if user.is_verified:
                return Response({'detail': 'Email is already verified'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete any existing tokens
            EmailVerificationToken.objects.filter(user=user).delete()
            
            # Create new verification token
            verification_token = EmailVerificationToken.objects.create(user=user)
            
            # Send verification email with code
            subjet = "Verify your email address"
            verification_message = f"""
Hello,

Please verify your email address to complete your registration.

Your verification code is: {verification_token.code}

If you didn't create an account, you can safely ignore this email.

Best regards,
The HireMod Team
"""
            msg = f"Subject: Verify your email address\n\n{verification_message}"
            smtp =smtplib.SMTP('smtp.elasticemail.com', port='2525')
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM, user.email, msg)
            smtp.quit()
            # send_mail(
            #     subject="Verify your email address",
            #     message=verification_message,
            #     from_email=settings.EMAIL_HOST_USER,
            #     recipient_list=[user.email],
            #     fail_silently=False,
            # )
            
            return Response({'detail': 'Verification code sent to your email'}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist for security reasons
            return Response({'detail': 'If this email exists in our system, a verification code has been sent'}, 
                         status=status.HTTP_200_OK)