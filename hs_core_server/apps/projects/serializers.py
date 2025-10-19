from rest_framework import serializers

from apps.generator.models import StorySegment
from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "created_at", "updated_at"]


class ProjectDetailSerializer(serializers.ModelSerializer):
    generation_status = serializers.SerializerMethodField()
    initial_video_url = serializers.SerializerMethodField()
    prompt = serializers.SerializerMethodField()

    # НОВОЕ:
    full_prompt = serializers.SerializerMethodField()
    last_video_url = serializers.SerializerMethodField()
    segments = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "created_at",
            "updated_at",
            "generation_status",
            "initial_video_url",
            "prompt",
            # новое
            "full_prompt",
            "last_video_url",
            "segments",
        ]

    def get_generation_status(self, obj):
        gen = getattr(obj, "initial_generation", None)
        return gen.status if gen else None

    def get_initial_video_url(self, obj):
        gen = getattr(obj, "initial_generation", None)
        return gen.initial_video_url if gen else None

    def get_prompt(self, obj):
        gen = getattr(obj, "initial_generation", None)
        return gen.prompt if gen else None

    def get_full_prompt(self, obj):
        last_seg = (
            StorySegment.objects.filter(project=obj).order_by("-position").first()
        )
        if last_seg:
            return last_seg.cumulative_prompt
        gen = getattr(obj, "initial_generation", None)
        return gen.prompt if gen else None

    def get_last_video_url(self, obj):
        last_seg = (
            StorySegment.objects.filter(project=obj).order_by("-position").first()
        )
        if last_seg:
            return last_seg.new_video_url
        gen = getattr(obj, "initial_generation", None)
        return gen.initial_video_url if gen else None

    def get_segments(self, obj):
        qs = StorySegment.objects.filter(project=obj).order_by("position")
        from apps.generator.serializers import StorySegmentSerializer

        return StorySegmentSerializer(qs, many=True).data
