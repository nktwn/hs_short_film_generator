# apps/projects/views.py (фрагмент)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import Project
from apps.projects.serializers import ProjectDetailSerializer, ProjectSerializer
from apps.projects.services import DeepSeekError, suggest_short_continuations


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("-created_at")
    serializer_class = ProjectSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectSerializer

    @action(detail=True, methods=["get"], url_path="suggest-continuations")
    def suggest_continuations(self, request, pk=None):
        project = self.get_object()
        prompt = request.query_params.get("prompt")

        if not prompt:
            detail_ser = ProjectDetailSerializer(project)
            prompt = detail_ser.data.get("prompt")

        if not prompt:
            return Response(
                {
                    "detail": "Prompt not found. Pass ?prompt=... or set initial_generation.prompt."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            suggestions = suggest_short_continuations(prompt=prompt, count=3, limit=20)
        except DeepSeekError as e:
            # Никаких фолбэков — отдаём 502
            return Response(
                {"detail": f"DeepSeek error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "project_id": str(project.id),
                "prompt": prompt,
                "suggestions": suggestions,
            }
        )
