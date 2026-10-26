from rest_framework import serializers
from django.contrib.auth.models import User
from .models import MemberProfile, RegistrationFormField, RegistrationFormSection

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

class DynamicMemberRegistrationSerializer(serializers.ModelSerializer):
    user = UserRegistrationSerializer()
    responses = serializers.JSONField()

    class Meta:
        model = MemberProfile
        fields = ['user', 'responses']

    def validate_responses(self, value):
        """
        Dynamically cross-references the submitted JSON answers against the 
        tenant's active Form Fields database configuration.
        """
        configured_fields = RegistrationFormField.objects.all()
        validated_data = {}

        for field in configured_fields:
            slug = field.field_name_slug
            user_answer = value.get(slug)

            # Check for required answers
            if field.is_required and user_answer in [None, "", [], {}]:
                raise serializers.ValidationError({slug: f"This field '{field.field_label}' is required by this welfare group."})

            # Check for choice validity on dropdown selection inputs
            if field.field_type == 'SELECT' and user_answer:
                allowed_choices = [c.strip() for c in field.choices.split(',') if c.strip()]
                if user_answer not in allowed_choices:
                    raise serializers.ValidationError({slug: f"Invalid choice. Must be one of: {', '.join(allowed_choices)}"})

            validated_data[slug] = user_answer

        return validated_data

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        responses_data = validated_data.pop('responses')

        # 1. Spin up base auth user
        user = User.objects.create_user(**user_data)

        # 2. Build profile carrying custom dynamic responses
        profile = MemberProfile.objects.create(
            user=user,
            custom_form_responses=responses_data
        )
        return profile
