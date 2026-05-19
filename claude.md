# Solidis — Gestion des Assurances Prêt Numérique (PAMF)

## Contexte métier

PAMF (Première Agence de MicroFinance Madagascar) soumet mensuellement des données de prêts
numériques à SOLIDIS (garant). Deux flux sont envoyés via SFTP :

| Flux | Dossier SFTP | Description |
|------|-------------|-------------|
| F2   | `/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/F2/` | Entrées initiales en portefeuille de garantie |
| EMG/ENCOURS | `/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/ENCOURS/` | Situation mensuelle des encours |

L'**appel de garantie** est déclenché quand un prêt atteint **61 jours d'arriérés** :
`montantAppelGaranti = Encours × 0.5`

---

## Stack technique

- **Backend** : Django (Python)
- **Frontend** : Vanilla JS (animations) + HTMX (requêtes backend)
- **Base de données** : SQL Server — `solidis` DB sur `172.20.24.37`
- **Core Banking** : base `CBS` (loLoan, loLoanBalanceOnDate, loLoanAllocation, loLoanDebit)
- **SFTP** : `34.209.31.76:3434`, user `pamf2`
- **Email** : Exchange / NTLM via `mail.pamf.mg`, compte `declaration.solidis@pamf.mg`

---

## UI / Design

- Thème clair, minimaliste (style Google)
- **Sidebar fixe** à gauche (navigation principale, comme les apps de gestion type Notion/Linear)
- HTMX pour les interactions sans rechargement de page

---

## Base de données existante (modèles non gérés par Django)

Tables alimentées par les scripts ETL. Django les lit uniquement (`managed = False`).

### `Solidis_initial_loan_v2` — portefeuille initial

| Colonne | Type | Description |
|---------|------|-------------|
| ID | int IDENTITY PK | |
| LOLOANID | float | ID prêt dans CBS |
| REF | varchar | Référence prêt |
| ID CREDIT | varchar | Numéro de prêt |
| N° CIN | bigint | Numéro CIN client |
| DATE DE NAISSANCE | varchar | |
| GENRE | varchar | M ou F |
| AGENCE D'OCTROI | varchar | Agence de décaissement |
| OBJET | varchar | Objet du prêt |
| CLASST | varchar | Segment client PAMF |
| MONTANT | bigint | Montant octroyé |
| DATOUV | date | Date de décaissement |
| DATECH | date | Date d'échéance / maturité |
| CYCLE | bigint | Cycle de prêt |
| TAUX | float | Taux d'intérêt |

```python
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
```

---

### `Solidis_loan_update_monthly_reports` — suivi mensuel

| Colonne | Type | Description |
|---------|------|-------------|
| id | int IDENTITY PK | |
| IDCREDIT | varchar(50) | Numéro de prêt |
| loLoanID | int | ID prêt CBS |
| CIN | varchar(30) | Numéro CIN |
| Encours | decimal(18,2) | Encours en principal |
| DaysInArrears | bigint | Jours de retard |
| reportDate | date | Date de la situation |

```python
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
```

---

## Modèles Django à créer

### `ProcesseAppelDeGarantie` — dossier d'appel de garantie (modèle parent)

Modèle central / mère. Chaque appel de garantie crée un dossier ici.
`ClientSituation` et `LoanRepaymentTransaction` sont ses enfants et portent la FK vers lui.

```python
class ProcesseAppelDeGarantie(models.Model):

    class Statut(models.TextChoices):
        EN_COURS  = 'en_cours',  'En cours'
        SOUMIS    = 'soumis',    'Soumis à SOLIDIS'
        ACCEPTE   = 'accepte',   'Accepté'
        REJETE    = 'rejete',    'Rejeté'
        REMBOURSE = 'rembourse', 'Remboursé'
    date_appel        = models.DateField(auto_now_add=True)
    date_from         = models.DateField()  # date début de la période d'appel
    date_to           = models.DateField()  # date fin de la période d'appel
    statut            = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    reference_solidis = models.CharField(max_length=100, blank=True, null=True)  # référence batch retournée par SOLIDIS

    class Meta:
        
        ordering = ['-date_from']
```

---

### `ClientSituation` — situation client à 61 jours (enfant du process)

Source : `get_situation_clients(date_from, date_to)` dans `Solidis_appel_garanti.py`

Filtre : `DaysInArrears = 61`

```python
class ClientSituation(models.Model):
    process               = models.ForeignKey(ProcesseAppelDeGarantie, on_delete=models.CASCADE, related_name='situations')
    idcredit              = models.CharField(max_length=50)
    lo_loan_id            = models.IntegerField()  # clé de jointure avec LoanRepaymentTransaction
    encours               = models.DecimalField(max_digits=18, decimal_places=2)
    montant_appel_garanti = models.DecimalField(max_digits=18, decimal_places=2)  # encours * 0.5
    days_in_arrears       = models.IntegerField()
    report_date           = models.DateField()
```

---

### `LoanRepaymentTransaction` — relevés de compte (enfants du process)

Source : `get_loan_repayment_transaction(date_from, date_to)` dans `Solidis_appel_garanti.py`

Jointures CBS : `loLoan` → `loLoanCredit` → `loLoanAllocation` → `loLoanDebit`  
Filtre : `DaysInArrears = 61`, `DebitType = 2`, `reportDate >= repaymentDate`

Un process peut avoir **plusieurs** transactions de remboursement.

```python
class LoanRepaymentTransaction(models.Model):
    process             = models.ForeignKey(ProcesseAppelDeGarantie, on_delete=models.CASCADE, related_name='transactions')
    idcredit            = models.CharField(max_length=50)
    lo_loan_id          = models.IntegerField()  # clé de jointure avec ClientSituation
    loan_amount_current = models.DecimalField(max_digits=18, decimal_places=2)
    encours             = models.DecimalField(max_digits=18, decimal_places=2)
    days_in_arrears     = models.IntegerField()
    report_date         = models.DateField()
    repayment_date      = models.DateField(null=True)
    total_paid          = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    trx_id              = models.IntegerField(null=True)
```

**Règles métier :**
- `ProcesseAppelDeGarantie` est créé pour lancer l'appel de garantie sur une période (`date_from` → `date_to`)
- `statut` et `reference_solidis` sont **globaux au batch** — un seul statut pour tout le process
- `ClientSituation` est `ForeignKey` (plusieurs situations client par process, une par prêt à 61 jours)
- `LoanRepaymentTransaction` est `ForeignKey` (plusieurs paiements possibles par process)
- `ClientSituation` et `LoanRepaymentTransaction` sont liés entre eux via `lo_loan_id` (pas de FK directe)
- Le `statut` du process est mis à jour manuellement ou via signal Django selon les transactions reçues

---

## Architecture Django

### Structure du projet

```
config/          ← projet Django (déjà créé via django-admin startproject config .)
    settings.py
    urls.py
garantie/        ← app principale à créer (manage.py startapp garantie)
    models.py        → tous les modèles ci-dessus
    views.py         → vues HTMX
    urls.py
    services.py      → logique métier (chargement CBS, calcul montant)
    templates/
        garantie/
```

### Flux "Lancer l'appel de garantie"

L'utilisateur déclenche le process depuis l'interface. Django orchestre tout :

```
[Vue HTMX "Lancer l'appel"]
    │
    ▼
services.lancer_appel(date_from, date_to)
    │
    ├─ 1. Créer ProcesseAppelDeGarantie(date_from, date_to, statut='en_cours')
    │
    ├─ 2. Requête CBS → get_situation_clients(date_from, date_to)
    │       → bulk_create ClientSituation (FK → process)
    │
    ├─ 3. Requête CBS → get_loan_repayment_transaction(date_from, date_to)
    │       → bulk_create LoanRepaymentTransaction (FK → process)
    │
    ├─ 4. Générer fichiers Excel (situation clients + transactions)
    │       → upload_df_to_sftp(df, '/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/appel_en_garantie', filename)
    │
    ├─ 5. process.statut = 'soumis' + save()
    │
    └─ 6. Retourner réponse HTMX (tableau récapitulatif)
```

`services.py` encapsule les requêtes SQL CBS, les insertions et l'upload SFTP — les vues ne font pas de SQL directement.

La fonction `upload_df_to_sftp` est partagée depuis `ETL_Solidis_monthly.py` — la porter dans `services.py` (ou un module utilitaire `sftp.py`) :

```python
def upload_df_to_sftp(df: pd.DataFrame, remote_path: str, filename: str):
    host     = "34.209.31.76"
    port     = 3434
    username = "pamf2"
    password = "TJLoRTlmAre@24"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        temp_file = tmp.name
        df.to_excel(temp_file, index=False, engine="openpyxl")

    try:
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            sftp.chdir(remote_path)
        except IOError:
            raise Exception(f"Remote path '{remote_path}' does not exist.")
        sftp.put(temp_file, f"{remote_path}/{filename}")
        sftp.close()
        transport.close()
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    return df
```

---

## Scripts ETL existants (hors Django)

| Fichier | Statut | Rôle |
|---------|--------|------|
| `ETL_Solidis.py` | **Obsolète — ne plus utiliser** | Ancien ETL quotidien remplacé par le mensuel |
| `ETL_Solidis_monthly.py` | Actif | Envoi F2 + EMG mensuel via SFTP, **alimente `Solidis_loan_update_monthly_reports`** |
| `Solidis_appel_garanti.py` | **Référence uniquement** | Contient les requêtes CBS source — logique portée dans `services.py` Django |

**`Solidis_initial_loan_v2`** : alimentée en dehors de ces scripts (source externe, pas gérée ici).

### Logique de validation KYC (`check_gender`)

La conformité CIN/genre est vérifiée avant l'envoi F2 :
- CIN[5] == `1` → Homme, CIN[5] == `2` → Femme
- Les prêts KO sont logués dans `Solidis_loan_KYC_KO` / `Solidis_loan_KYC_KO_new`

### Notifications email

| Cas | Destinataires | Déclencheur |
|-----|--------------|-------------|
| `success` | `gpp@solidis.org` + équipe interne | Upload SFTP OK |
| `no_data` | Équipe interne | df_emg vide |
| `no_submissions` | Équipe interne | Aucune soumission éligible |
| `delete_failure` | Équipe interne | Échec suppression avant re-run |

---

## Conventions de développement

- Connexion SQL Server : `pyodbc` (lecture) + `SQLAlchemy` (écriture via `to_sql`)
- Toujours supprimer les données existantes avant un re-run (éviter les doublons)
- Paramètres de requêtes SQL : utiliser `.format()` ou requêtes paramétrées — **pas de concaténation directe**
- Multi-plateforme : détecter `platform.system()` pour choisir le driver ODBC (`SQL Server` sur Windows, `ODBC Driver 17` sur Linux)


---

## Module Commission

### Contexte métier

PAMF doit payer à SOLIDIS deux types de commissions mensuelles sur le portefeuille de prêts numériques garantis. Les deux commissions sont calculées à **1,5 % de l'Encours** et extraites depuis `Solidis_loan_update_monthly_reports` (jointure CBS).

| Type | Déclencheur | Label |
|------|------------|-------|
| Commission 1 | Entrée en portefeuille : `DaysInArrears = 0` **ET** `reportDate = AgreementDate` | `Commission 1 - 1.5%` |
| Commission 2 | 30 jours d'arriérés : `DaysInArrears = 30` | `Commission 2 - 1.5%` |

**Formule :** `commission = Encours × 0.015`

---

### Requête CBS source

```sql
SELECT
    r.id,
    r.IDCREDIT,
    r.loLoanID,
    r.Encours,
    r.Encours * 0.015          AS commission,
    r.DaysInArrears,
    r.reportDate,
    CASE
        WHEN r.DaysInArrears = 0  THEN 'Commission 1 - 1.5%'
        WHEN r.DaysInArrears = 30 THEN 'Commission 2 - 1.5%'
    END AS commission_type
FROM solidis.dbo.Solidis_loan_update_monthly_reports r
JOIN cbs.dbo.loLoan l ON l.loLoanID = r.loLoanID
WHERE (
    r.DaysInArrears = 30
    OR (r.DaysInArrears = 0 AND r.reportDate = l.AgreementDate)
)
AND r.reportDate BETWEEN :date_from AND :date_to
```

---

### Modèles Django

#### `CommissionProcess` — dossier de commission (modèle parent)

Même structure que `ProcesseAppelDeGarantie` : un process par période, statut et référence globaux au batch.

```python
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
```

#### `CommissionDetail` — ligne de commission (enfant)

```python
class CommissionDetail(models.Model):
    process         = models.ForeignKey(CommissionProcess, on_delete=models.CASCADE, related_name='details')
    idcredit        = models.CharField(max_length=50)
    lo_loan_id      = models.IntegerField()
    encours         = models.DecimalField(max_digits=18, decimal_places=2)
    commission      = models.DecimalField(max_digits=18, decimal_places=2)  # encours * 0.015
    commission_type = models.CharField(max_length=30)  # 'Commission 1 - 1.5%' | 'Commission 2 - 1.5%'
    days_in_arrears = models.IntegerField()
    report_date     = models.DateField()
```

---

### Flux "Lancer la commission"

Même pattern que `lancer_appel` dans `services.py` :

```
services.lancer_commission(date_from, date_to)
    │
    ├─ 1. Créer CommissionProcess(date_from, date_to, statut='en_cours')
    │
    ├─ 2. Requête CBS → _get_commissions(date_from, date_to)
    │       → bulk_create CommissionDetail (FK → process)
    │
    ├─ 3. Générer fichier Excel (détails commissions)
    │       → upload_df_to_sftp(df, '/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/commission', filename)
    │
    ├─ 4. process.statut = 'soumis' + save()
    │
    └─ 5. Retourner process (réponse HTMX)
```

---

### App Django

- **App** : `commission/` (à créer via `manage.py startapp commission`)
- **URL** : `/commission/`
- **Navigation sidebar** : lien "Commissions" sous "Appels de garantie"
- **Pages** : dashboard commissions + détail par process (même structure UI que `garantie/`)
