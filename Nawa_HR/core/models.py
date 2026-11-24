import uuid

from django.db import models


class PublicIdModel(models.Model):
    """
    Give a model a public UUID, used in URLs and API responses.

    The auto-increment ``id`` stays internal: foreign keys and joins use it,
    but it never leaves the API.
    """

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        abstract = True
