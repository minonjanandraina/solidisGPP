from django.db import models


class DeclarationConfig(models.Model):
    """
    Configuration dynamique du gating F2 (partagée avec ETL_Solidis_monthly.py, qui lit/écrit
    la même table via SQL brut). Ligne unique (singleton).
    """
    plafond_emg       = models.DecimalField(max_digits=18, decimal_places=2, default=5_000_000_000)
    seuil_reprise_pct = models.DecimalField(max_digits=5, decimal_places=4, default=0.80)
    f2_bloque         = models.BooleanField(default=False)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Solidis_declaration_config'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def seuil_reprise(self):
        return self.plafond_emg * self.seuil_reprise_pct

    def __str__(self):
        return f"Plafond {self.plafond_emg} — seuil reprise {self.seuil_reprise_pct * 100:.0f}%"


class DeclarationProcess(models.Model):

    class Statut(models.TextChoices):
        EN_COURS         = 'en_cours',         'En cours'
        SOUMIS            = 'soumis',           'Soumis à SOLIDIS'
        F2_BLOQUE         = 'f2_bloque',        'F2 suspendu (EMG envoyé)'
        SANS_DONNEES      = 'sans_donnees',     'Aucune donnée EMG'
        SANS_SOUMISSION   = 'sans_soumission',  'Aucune soumission éligible'
        ECHEC             = 'echec',            'Échec'

    date_process        = models.DateTimeField(auto_now_add=True)
    date                 = models.DateField()  # une date = un process (extraction + déclaration EMG + F2 de ce jour)
    statut               = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    reference_solidis    = models.CharField(max_length=100, blank=True, null=True)

    f2_bloque            = models.BooleanField(default=False)  # F2 bloqué ce jour-là (encours j-1 au-dessus du seuil)
    emg_lignes           = models.IntegerField(default=0)
    emg_encours_total    = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    f2_lignes            = models.IntegerField(default=0)
    f2_lignes_exclues    = models.IntegerField(default=0)  # candidats F2 de ce jour non déclarés (F2 bloqué)
    message               = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Solidis_declaration_process'
        ordering = ['-date']

    def __str__(self):
        return f"Déclaration {self.date} [{self.get_statut_display()}]"


class SolidisF2Declared(models.Model):
    """Lecture de solidis.dbo.Solidis_f2_declared_v2, alimentée par ETL_Solidis_monthly.py (même structure que Solidis_initial_loan_v2)."""
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
    date_declaration  = models.DateField(db_column='DATE_DECLARATION', null=True)

    class Meta:
        managed = False
        db_table = 'Solidis_f2_declared_v2'
