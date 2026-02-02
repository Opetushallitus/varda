from rest_framework.serializers import Serializer, BooleanField, FileField


# Serializers define the API representation.
class UploadSerializer(Serializer):
    file_uploaded = FileField(required=True)
    change_private_key = BooleanField(required=False)

    class Meta:
        fields = ["file_uploaded", "change_private_key"]
