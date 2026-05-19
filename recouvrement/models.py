from django.db import models


class RecouvrementProcess(models.Model):

    class Statut(models.TextChoices):
        EN_COURS  = 'en_cours',  'En cours'
        SOUMIS    = 'soumis',    'Soumis à SOLIDIS'
        ACCEPTE   = 'accepte',   'Accepté'
        REJETE    = 'rejete',    'Rejeté'
        REMBOURSE = 'rembourse', 'Remboursé'

    date_process      = models.DateField(auto_now_add=True)
    date_from         = models.DateField()
    date_to           = models.DateField()
    statut            = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    reference_solidis = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-date_from']

    def __str__(self):
        return f"Recouvrement {self.date_from} → {self.date_to} [{self.get_statut_display()}]"


class RecouvrementTransaction(models.Model):
    process                        = models.ForeignKey(RecouvrementProcess, on_delete=models.CASCADE, related_name='transactions')
    idcredit                       = models.CharField(max_length=50)
    lo_loan_id                     = models.IntegerField()
    agreement_number               = models.CharField(max_length=100, null=True)
    agreement_date                 = models.DateField(null=True)
    loan_amount                    = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    encours_au_moment_appel        = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    total_remboursement_principale = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    recouvrement_a_reverser        = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    last_allocation_id             = models.BigIntegerField(null=True)

    class Meta:
        ordering = ['agreement_date', 'idcredit']
