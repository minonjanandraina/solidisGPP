from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='RecouvrementProcess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_process', models.DateField(auto_now_add=True)),
                ('date_from', models.DateField()),
                ('date_to', models.DateField()),
                ('statut', models.CharField(
                    choices=[
                        ('en_cours',  'En cours'),
                        ('soumis',    'Soumis à SOLIDIS'),
                        ('accepte',   'Accepté'),
                        ('rejete',    'Rejeté'),
                        ('rembourse', 'Remboursé'),
                    ],
                    default='en_cours',
                    max_length=20,
                )),
                ('reference_solidis', models.CharField(blank=True, max_length=100, null=True)),
            ],
            options={'ordering': ['-date_from']},
        ),
        migrations.CreateModel(
            name='RecouvrementTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idcredit', models.CharField(max_length=50)),
                ('lo_loan_id', models.IntegerField()),
                ('agreement_number', models.CharField(max_length=100, null=True)),
                ('agreement_date', models.DateField(null=True)),
                ('loan_amount', models.DecimalField(decimal_places=2, max_digits=18, null=True)),
                ('encours_au_moment_appel', models.DecimalField(decimal_places=2, max_digits=18, null=True)),
                ('total_remboursement_principale', models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ('recouvrement_a_reverser', models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ('last_allocation_id', models.BigIntegerField(null=True)),
                ('process', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transactions',
                    to='recouvrement.recouvrementprocess',
                )),
            ],
            options={'ordering': ['agreement_date', 'idcredit']},
        ),
    ]
