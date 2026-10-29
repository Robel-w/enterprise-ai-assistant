from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0013_answerresult_document")]

    operations = [
        migrations.AddField(
            model_name="evaluationquestion",
            name="evidence_snippet",
            field=models.TextField(blank=True),
        ),
    ]
