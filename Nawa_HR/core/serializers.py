from rest_framework import serializers


class PublicIdSerializer(serializers.ModelSerializer):
    """
    Show a model's public UUID to clients as "id".

    The internal database id never leaves the API. Subclasses set their
    own Meta and include "id" in its fields.
    """

    id = serializers.UUIDField(source="public_id", read_only=True)
