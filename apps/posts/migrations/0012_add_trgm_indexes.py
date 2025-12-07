from django.db import migrations
from django.contrib.postgres.indexes import GinIndex

class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0011_enable_pg_trgm"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="post",
            index=GinIndex(
                fields=["title"],
                name="post_title_trgm_gin",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="post",
            index=GinIndex(
                fields=["short_description"],
                name="post_shdesc_trgm_gin",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="post",
            index=GinIndex(
                fields=["text_content"],
                name="post_text_trgm_gin",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="post",
            index=GinIndex(
                fields=["slug"],
                name="post_slug_trgm_gin",
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]
