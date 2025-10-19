from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generator.models import StorySegment
from apps.generator.serializers import (
    ContinueRequestSerializer,
    DeleteLastRequestSerializer,
    StorySegmentSerializer,
)
from apps.generator.services import PipelineError, continue_pipeline
from apps.generator.services_assemble import assemble_videos_to_media
from apps.projects.models import Project


def _absolutize(request, url: str) -> str:
    # Если MEDIA_URL уже абсолютный (CDN и т.п.) — вернём как есть
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return request.build_absolute_uri(url)


def _concat_prompts(previous_prompt: str, next_prompt: str) -> str:
    """
    Красиво склеивает промпты:
    - добавляет точку, если в конце previous_prompt нет терминатора.
    - ставит пробел между частями.
    """
    prev = (previous_prompt or "").strip()
    nxt = (next_prompt or "").strip()
    if not prev:
        return nxt
    if prev.endswith((".", "!", "?", "…")):
        return f"{prev} {nxt}".strip()
    return f"{prev}. {nxt}".strip()


def _get_last_state(project: Project):
    """
    Возвращает:
      - previous_video_url
      - previous_prompt (полный текущий промпт)
      - next_position
    Источник previous_video_url:
      1) Если есть StorySegment — берём new_video_url из последнего
      2) Иначе берём initial_generation.initial_video_url (если есть)
    Источник previous_prompt:
      1) Если есть StorySegment — cumulative_prompt последнего
      2) Иначе initial_generation.prompt (если есть)
    """
    last_seg = project.story_segments.order_by("-position").first()
    if last_seg:
        previous_video_url = last_seg.new_video_url
        previous_prompt = last_seg.cumulative_prompt
        next_position = last_seg.position + 1
        return previous_video_url, previous_prompt, next_position

    # Нет частей — используем initial_generation
    gen = getattr(project, "initial_generation", None)
    if not gen or not gen.initial_video_url or not gen.prompt:
        return None, None, 0
    return gen.initial_video_url, gen.prompt, 0


class StorySegmentViewSet(viewsets.ModelViewSet):
    """
    CRUD поверх StorySegment.
    По умолчанию:
      - list можно фильтровать по project_id (?project_id=<uuid>)
      - destroy разрешён ТОЛЬКО для последней части проекта (иначе 400)
    Доп. экшены:
      - POST /api/generator/continue/  (создать следующую часть)
      - POST /api/generator/delete-last/ (удалить последнюю часть проекта)
    """

    queryset = StorySegment.objects.select_related("project").all()
    serializer_class = StorySegmentSerializer

    def list(self, request, *args, **kwargs):
        project_id = request.query_params.get("project_id")
        qs = self.get_queryset()
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = qs.order_by("project", "position")
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)

    def destroy(self, request, *args, **kwargs):
        """
        Разрешаем удалять только ПОСЛЕДНЮЮ часть истории проекта.
        """
        instance: StorySegment = self.get_object()
        last_seg = (
            StorySegment.objects.filter(project=instance.project)
            .order_by("-position")
            .first()
        )
        if not last_seg or last_seg.id != instance.id:
            return Response(
                {
                    "detail": "Можно удалять только последнюю часть истории этого проекта."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="continue")
    def continue_story(self, request):
        """
        Создаёт следующую часть истории.
        body: { "project_id": "<uuid>", "next_prompt": "<text>" }
        """
        ser = ContinueRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project_id = ser.validated_data["project_id"]
        next_prompt = ser.validated_data["next_prompt"]

        project = get_object_or_404(Project, id=project_id)

        previous_video_url, previous_prompt, next_position = _get_last_state(project)
        if not previous_video_url or not previous_prompt:
            return Response(
                {
                    "detail": "Нельзя продолжить: нет исходного видео или промпта. "
                    "Убедитесь, что создан initial_generation и у него есть prompt и initial_video_url."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pipe_resp = continue_pipeline(
                previous_video_url=previous_video_url,
                previous_prompt=previous_prompt,
                next_prompt=next_prompt,
            )
        except PipelineError as e:
            return Response(
                {"detail": f"Pipeline error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            return Response({"detail": f"Unexpected error: {str(e)}"}, status=500)

        # ожидаемая схема ответа:
        # {
        #   "new_video_url": "...",
        #   "used_prompt": "...",
        #   "job_set_id": "...",
        #   "frame_image_url": "...",
        #   "meta": { ... }
        # }
        new_video_url = pipe_resp.get("new_video_url")
        used_prompt = pipe_resp.get("used_prompt", next_prompt)
        job_set_id = pipe_resp.get("job_set_id")
        frame_image_url = pipe_resp.get("frame_image_url")
        meta = pipe_resp.get("meta")

        if not new_video_url:
            return Response(
                {"detail": "Pipeline не вернул new_video_url."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        cumulative_prompt = _concat_prompts(previous_prompt, used_prompt)

        with transaction.atomic():
            seg = StorySegment.objects.create(
                project=project,
                position=next_position,
                previous_video_url=previous_video_url,
                previous_prompt=previous_prompt,
                used_prompt=used_prompt,
                new_video_url=new_video_url,
                cumulative_prompt=cumulative_prompt,
                job_set_id=job_set_id,
                frame_image_url=frame_image_url,
                meta=meta,
            )

        return Response(
            StorySegmentSerializer(seg).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="delete-last")
    def delete_last(self, request):
        """
        Удаляет последнюю часть истории проекта.
        body: { "project_id": "<uuid>" }
        """
        ser = DeleteLastRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project_id = ser.validated_data["project_id"]
        project = get_object_or_404(Project, id=project_id)

        last_seg = project.story_segments.order_by("-position").first()
        if not last_seg:
            return Response(
                {"detail": "У проекта нет частей для удаления."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        last_seg.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="assemble")
    def assemble(self, request):
        """
        POST /api/generator/assemble/
        body: { "project_id": "<uuid>" }
        """
        project_id = request.data.get("project_id")
        if not project_id:
            return Response({"detail": "project_id is required"}, status=400)

        project = get_object_or_404(Project, id=project_id)

        parts = []
        gen = getattr(project, "initial_generation", None)
        if gen and gen.initial_video_url:
            parts.append(gen.initial_video_url)
        for s in project.story_segments.order_by("position").all():
            if s.new_video_url:
                parts.append(s.new_video_url)

        if not parts:
            return Response({"detail": "No videos to assemble for this project."}, status=400)

        try:
            # services_assemble возвращает MEDIA_URL + path (может быть относительным)
            media_url = assemble_videos_to_media(str(project.id), parts)
        except Exception as e:
            return Response({"detail": f"Assemble error: {e}"}, status=502)

        full_url = _absolutize(request, media_url)
        return Response(
            {
                "project_id": str(project.id),
                "assembled_url": full_url,   # <— теперь абсолютный
            },
            status=status.HTTP_200_OK,
        )