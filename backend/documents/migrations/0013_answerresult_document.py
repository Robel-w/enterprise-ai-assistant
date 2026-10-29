import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0012_enable_vector_extension")]

    operations = [
        migrations.AddField(
            model_name="answerevaluationresult",
            name="document",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="answer_evaluation_results",
                to="documents.document",
            ),
        ),
    ]
