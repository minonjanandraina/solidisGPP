from django.db import models


class SolidisInitialLoan(models.Model):
    loloanid          = models.FloatField(db_column='LOLOANID', null=True)
    ref               = models.TextField(db_column='REF', null=True)
    id_credit         = models.TextField(db_column='ID CREDIT', null=True)
    cin               = models.BigIntegerField(db_column='N° CIN', null=True)
    date_de_naissance = models.TextField(db_column='DATE DE NAISSANCE', null=True)
    genre             = models.TextField(db_column='GENRE', null=True)
    agence_octroi     = models.TextField(db_column="AGENCE D'OCTROI", null=True)
    objet             = models.TextField(db_column='OBJET', null=True)
    classt            = models.TextField(db_column='CLASST', null=True)
    montant           = models.BigIntegerField(db_column='MONTANT', null=True)
    datouv            = models.DateField(db_column='DATOUV', null=True)
    datech            = models.DateField(db_column='DATECH', null=True)
    cycle             = models.BigIntegerField(db_column='CYCLE', null=True)
    taux              = models.FloatField(db_column='TAUX', null=True)

    class Meta:
        managed = False
        db_table = 'Solidis_initial_loan_v2'


class SolidisLoanMonthlyReport(models.Model):
    idcredit        = models.CharField(max_length=50, db_column='IDCREDIT')
    lo_loan_id      = models.IntegerField(db_column='loLoanID')
    cin             = models.CharField(max_length=30, db_column='CIN', null=True)
    encours         = models.DecimalField(max_digits=18, decimal_places=2, db_column='Encours', null=True)
    days_in_arrears = models.BigIntegerField(db_column='DaysInArrears', null=True)
    report_date     = models.DateField(db_column='reportDate', null=True)

    class Meta:
        managed = False
        db_table = 'Solidis_loan_update_monthly_reports'


class ProcesseAppelDeGarantie(models.Model):

    class Statut(models.TextChoices):
        EN_COURS  = 'en_cours',  'En cours'
        SOUMIS    = 'soumis',    'Soumis à SOLIDIS'
        ACCEPTE   = 'accepte',   'Accepté'
        REJETE    = 'rejete',    'Rejeté'
        REMBOURSE = 'rembourse', 'Remboursé'

    date_appel        = models.DateField(auto_now_add=True)
    date_from         = models.DateField()
    date_to           = models.DateField()
    statut            = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    reference_solidis = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-date_from']

    @property
    def montant_total(self):
        return sum(s.montant_appel_garanti for s in self.situations.all()) or 0

    def __str__(self):
        return f"Appel {self.date_from} → {self.date_to} [{self.get_statut_display()}]"


class ClientSituation(models.Model):
    process               = models.ForeignKey(ProcesseAppelDeGarantie, on_delete=models.CASCADE, related_name='situations')
    idcredit              = models.CharField(max_length=50)
    lo_loan_id            = models.IntegerField()
    encours               = models.DecimalField(max_digits=18, decimal_places=2)
    montant_appel_garanti = models.DecimalField(max_digits=18, decimal_places=2)
    days_in_arrears       = models.IntegerField()
    report_date           = models.DateField()

    class Meta:
        ordering = ['idcredit']

    def __str__(self):
        return f"{self.idcredit} — {self.montant_appel_garanti}"


class LoanRepaymentTransaction(models.Model):
    process             = models.ForeignKey(ProcesseAppelDeGarantie, on_delete=models.CASCADE, related_name='transactions')
    idcredit            = models.CharField(max_length=50)
    lo_loan_id          = models.IntegerField()
    loan_amount_current = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    encours             = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    days_in_arrears     = models.IntegerField(null=True)
    report_date         = models.DateField(null=True)
    repayment_date      = models.DateField(null=True)
    total_paid          = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    trx_id              = models.IntegerField(null=True)

    class Meta:
        ordering = ['idcredit', 'repayment_date']

    def __str__(self):
        return f"{self.idcredit} — payé {self.total_paid}"
