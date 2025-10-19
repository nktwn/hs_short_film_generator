from rest_framework import serializers

from apps.generator.models import StorySegment


class StorySegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorySegment
        fields = [
            "id",
            "project",
            "position",
            "previous_video_url",
            "previous_prompt",
            "used_prompt",
            "new_video_url",
            "cumulative_prompt",
            "job_set_id",
            "frame_image_url",
            "meta",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "position",
            "previous_video_url",
            "previous_prompt",
            "new_video_url",
            "cumulative_prompt",
            "job_set_id",
            "frame_image_url",
            "meta",
            "created_at",
            "updated_at",
        ]


class ContinueRequestSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    next_prompt = serializers.CharField(
        allow_blank=False, allow_null=False, trim_whitespace=True
    )


class DeleteLastRequestSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
