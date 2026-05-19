from django.db import models


class CommissionProcess(models.Model):

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

    @property
    def commission_total(self):
        return sum(d.commission for d in self.details.all()) or 0

    def __str__(self):
        return f"Commission {self.date_from} → {self.date_to} [{self.get_statut_display()}]"


class CommissionDetail(models.Model):
    process         = models.ForeignKey(CommissionProcess, on_delete=models.CASCADE, related_name='details')
    idcredit        = models.CharField(max_length=50)
    lo_loan_id      = models.IntegerField()
    encours         = models.DecimalField(max_digits=18, decimal_places=2)
    commission      = models.DecimalField(max_digits=18, decimal_places=2)
    commission_type = models.CharField(max_length=30)
    days_in_arrears = models.IntegerField()
    report_date     = models.DateField()

    class Meta:
        ordering = ['commission_type', 'idcredit']

    def __str__(self):
        return f"{self.idcredit} — {self.commission_type} — {self.commission}"
