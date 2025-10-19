from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.initial_generator.models import InitialVideoGeneration
from apps.initial_generator.serializers import InitialVideoGenerationSerializer
from apps.initial_generator.services import get_generation_status, start_generation
from apps.projects.models import Project


class InitialVideoGenerationViewSet(viewsets.ModelViewSet):
    queryset = InitialVideoGeneration.objects.all().order_by("-created_at")
    serializer_class = InitialVideoGenerationSerializer

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """
        POST /api/initial_generator/generate/
        body: { "project_id": "<uuid>", "prompt": "<text>" }
        """
        project_id = request.data.get("project_id")
        prompt = request.data.get("prompt")
        if not project_id or not prompt:
            return Response({"error": "project_id and prompt are required"}, status=400)

        project = get_object_or_404(Project, id=project_id)

        try:
            external_resp = start_generation(prompt)
        except Exception as e:
            return Response({"error": f"External API error: {str(e)}"}, status=500)

        job_id = external_resp.get("job_id")
        status_val = external_resp.get("status", "queued")

        gen = InitialVideoGeneration.objects.create(
            project=project, job_id=job_id, prompt=prompt, status=status_val
        )

        return Response(
            InitialVideoGenerationSerializer(gen).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"], url_path="check-status")
    def check_status(self, request, pk=None):
        """
        GET /api/initial_generator/<uuid>/check-status/
        Обновляет статус и initial_video_url из внешнего API (устойчиво к null'ам).
        """
        generation = get_object_or_404(InitialVideoGeneration, pk=pk)

        # Если по какой-то причине job_id отсутствует — корректно сообщим об этом
        if not generation.job_id:
            return Response(
                {"error": "job_id is empty for this generation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = get_generation_status(generation.job_id)
        except Exception as e:
            return Response({"error": f"External API error: {str(e)}"}, status=500)

        # 1) Обновим общий статус из внешнего ответа (queued/in_progress/completed/failed)
        new_status = data.get("status") or generation.status
        generation.status = new_status

        # 2) Попробуем вытащить video_url максимально безопасно
        #    2.1 — верхнеуровневый video_url (он может быть строкой или null)
        video_url = (
            (((data.get("meta") or {}).get("jobs") or [{}])[0].get("results") or {})
            .get("raw", {})
            .get("url")
        )

        if not video_url:
            #    2.2 — из meta.jobs[0].results.raw.url (results может быть null!)
            meta = data.get("meta") or {}
            jobs = meta.get("jobs") or []
            first_job = jobs[0] if jobs else {}
            results = first_job.get("results") or {}
            raw = results.get("raw") or {}
            url_from_raw = raw.get("url") or None
            if url_from_raw:
                video_url = url_from_raw

        # 3) Если есть ссылка — сохраняем и помечаем completed (на случай, если внешний статус задержался)
        if video_url:
            generation.initial_video_url = video_url
            generation.status = "completed"

        # 4) Если внешний сервис сказал failed — фиксируем в БД
        if new_status == "failed":
            generation.initial_video_url = (
                None  # на всякий случай, чтобы не было "старой" ссылки
            )

        generation.save(update_fields=["status", "initial_video_url", "updated_at"])
        return Response(InitialVideoGenerationSerializer(generation).data)
