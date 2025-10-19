from rest_framework import serializers

from apps.initial_generator.models import InitialVideoGeneration


class InitialVideoGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InitialVideoGeneration
        fields = [
            "id",
            "project",
            "prompt",
            "job_id",
            "initial_video_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "job_id",
            "initial_video_url",
            "status",
            "created_at",
            "updated_at",
        ]
