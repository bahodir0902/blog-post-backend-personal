from django.contrib import admin
from .models import (
    Comment,
    CommentEditHistory,
    CommentReaction
)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    pass


@admin.register(CommentEditHistory)
class CommentEditHistoryAdmin(admin.ModelAdmin):
    pass

@admin.register(CommentReaction)
class CommentReactionAdmin(admin.ModelAdmin):
    pass