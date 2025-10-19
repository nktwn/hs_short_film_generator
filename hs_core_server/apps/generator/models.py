import uuid

from django.db import models
from django.utils import timezone

from apps.projects.models import Project


class StorySegment(models.Model):
    """
    Одна "часть" продолжения истории для проекта.
    Порядок задаётся полем position (0,1,2,...).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="story_segments", db_index=True
    )
    position = models.PositiveIntegerField(help_text="Позиция части в истории (0..N)")

    # Данные из внешнего пайплайна
    previous_video_url = models.URLField(
        help_text="Видео, на основе которого сгенерировано", max_length=1024
    )
    previous_prompt = models.TextField(help_text="Промпт до добавления этой части")
    used_prompt = models.TextField(help_text="Промпт, добавленный в этой части")
    new_video_url = models.URLField(
        help_text="Результирующее видео этой части", max_length=1024
    )

    # Служебные/метаданные
    cumulative_prompt = models.TextField(help_text="Полный промпт на данном шаге")
    job_set_id = models.CharField(max_length=255, blank=True, null=True)
    frame_image_url = models.URLField(blank=True, null=True, max_length=1024)
    meta = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("project", "position"),)
        indexes = [
            models.Index(fields=["project", "position"]),
        ]
        ordering = ["project", "position"]

    def __str__(self):
        return f"{self.project.name} — part #{self.position}"
