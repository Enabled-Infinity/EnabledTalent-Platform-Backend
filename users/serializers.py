from rest_framework import serializers
from .models import User,Profile,Feedback


class UserCreateSerializer(serializers.ModelSerializer):
    confirm_password= serializers.CharField(max_length=100)
    invite_code= serializers.CharField(required=False)

    class Meta:
        model= User
        write_only= ["password", "confirm_password"]
        fields= ['email', 'password', 'confirm_password', 'invite_code', 'newsletter']

    def create(self, validated_data):
        if validated_data["password"] == validated_data["confirm_password"]:
             return User.objects.create_user(
                email=validated_data["email"], password=validated_data["password"]
                )
        else:
            return  serializers.ValidationError("Password and confirmation do not match.")


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        read_only = ["referral_code", "user"]
        fields = (
            "id",
            "user",
            "avatar",
            "referral_code",
            "total_referrals",
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "email", 
            "last_name",
            "avatar"
        )
    
    def update(self, instance, validated_data):
        avatar = validated_data.pop('avatar', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update avatar in profile
        if avatar is not None:
            profile, created = Profile.objects.get_or_create(user=instance)
            profile.avatar = avatar
            profile.save()
        return instance

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    profile= ProfileSerializer()
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "email",
            "last_name",
            "is_active",
            "profile",
            "is_verified"
        )
        
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create profile related to the user
        if profile_data:
            profile_instance = getattr(instance, 'profile', None)
            if profile_instance:
                # Update existing profile
                profile_serializer = ProfileSerializer(profile_instance, data=profile_data, partial=True)
                if profile_serializer.is_valid():
                    profile_serializer.save()
            else:
                # Create new profile if it doesn't exist
                Profile.objects.create(user=instance, **profile_data)
        
        return instance
    


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True,write_only=True)
    new_password = serializers.CharField(required=True,write_only=True)
    confirm_new_password= serializers.CharField(required=True,write_only=True)



class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ("urgency", "subject", "message", "emoji", "attachment")