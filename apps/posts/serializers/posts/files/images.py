from rest_framework import serializers

from apps.posts.models import PostImage


class PostImageReadSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()

    class Meta:
        model = PostImage
        fields = [
            "id",
            "post",
            "image",
            "alt_text",
            "caption",
            "sort_order",
            "file_name",
            "file_size",
            "content_type",
            "file_url",
            "is_image",
        ]

    def get_file_name(self, instance: PostImage):
        return instance.original_name

    def get_file_size(self, instance: PostImage):
        return instance.size

    def get_content_type(self, instance: PostImage):
        return instance.content_type

    def get_file_url(self, instance: PostImage):
        if instance.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(instance.image.url)
            return instance.image.url
        return None

    def get_is_image(self, instance: PostImage):
        if instance.image:
            ext = instance.image.name.split(".")[-1]
            if ext in ["jpg", "jpeg", "png"]:
                return True
        return False
