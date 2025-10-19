import uuid

from django.db import models

from apps.projects.models import Project


class InitialVideoGeneration(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="initial_generation"
    )

    job_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    prompt = models.TextField()
    initial_video_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="queued")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"InitialVideo for {self.project.name} ({self.status})"
