from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('posts', '0010_post_text_content_alter_post_content')
    ]

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            "DROP EXTENSION IF EXISTS pg_trgm;"
        )
    ]
