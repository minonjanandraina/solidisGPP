import contextlib
import datetime
import io
import platform

import pandas as pd
import pyodbc

import ETL_Solidis_monthly as etl

from .models import DeclarationConfig, DeclarationProcess


def _get_conx():
    driver = "ODBC Driver 17 for SQL Server" if platform.system() == "Linux" else "SQL Server"
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )


_CASE_TO_STATUT = {
    "success":         DeclarationProcess.Statut.SOUMIS,
    "f2_bloque":       DeclarationProcess.Statut.F2_BLOQUE,
    "no_data":         DeclarationProcess.Statut.SANS_DONNEES,
    "no_submissions":  DeclarationProcess.Statut.SANS_SOUMISSION,
    "delete_failure":  DeclarationProcess.Statut.ECHEC,
}

_CASE_TO_MESSAGE = {
    "success":         "F2 et EMG envoyés avec succès.",
    "f2_bloque":       "Encours au-dessus du seuil de reprise : F2 suspendu, EMG envoyé.",
    "no_data":         "Aucune donnée EMG pour cette période.",
    "no_submissions":  "Aucune soumission F2 éligible pour cette période.",
    "delete_failure":  "Échec de la suppression des données existantes — envoi annulé.",
}


def get_config() -> DeclarationConfig:
    return DeclarationConfig.get_solo()


def update_config(plafond_emg, seuil_reprise_pct) -> DeclarationConfig:
    config = DeclarationConfig.get_solo()
    config.plafond_emg = plafond_emg
    config.seuil_reprise_pct = seuil_reprise_pct
    config.save(update_fields=["plafond_emg", "seuil_reprise_pct", "updated_at"])
    return config


def _daterange(date_from: str, date_to: str):
    d0 = datetime.date.fromisoformat(str(date_from))
    d1 = datetime.date.fromisoformat(str(date_to))
    d = d0
    while d <= d1:
        yield d
        d += datetime.timedelta(days=1)


def _run_one_day(d: datetime.date) -> tuple:
    # supprime l'historique existant pour cette date avant de relancer (évite les doublons en cas de re-run)
    DeclarationProcess.objects.filter(date=d).delete()
    process = DeclarationProcess.objects.create(date=d, statut=DeclarationProcess.Statut.EN_COURS)
    d_str = d.isoformat()

    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log):
            summary = etl.main(d_str, d_str)
    except Exception as exc:
        process.statut = DeclarationProcess.Statut.ECHEC
        process.message = f"{exc}\n\n{log.getvalue()}"
        process.save(update_fields=["statut", "message"])
        return process, None

    case = (summary or {}).get("case")
    process.statut = _CASE_TO_STATUT.get(case, DeclarationProcess.Statut.ECHEC)
    process.f2_bloque = bool((summary or {}).get("f2_bloque") or False)
    process.emg_lignes = int((summary or {}).get("emg_lignes") or 0)
    process.emg_encours_total = (summary or {}).get("emg_encours_total") or 0
    process.f2_lignes = int((summary or {}).get("f2_lignes") or 0)
    process.f2_lignes_exclues = int((summary or {}).get("f2_lignes_exclues") or 0)
    process.message = _CASE_TO_MESSAGE.get(case, "Résultat inattendu.") + "\n\n" + log.getvalue()
    process.save(update_fields=[
        "statut", "f2_bloque",
        "emg_lignes", "emg_encours_total",
        "f2_lignes", "f2_lignes_exclues", "message",
    ])
    return process, summary


def lancer_declaration(date_from: str, date_to: str, retry: bool = False) -> list:
    """
    Déclenche ETL_Solidis_monthly.main() jour par jour sur [date_from, date_to].
    Un DeclarationProcess = une date = une extraction + déclaration EMG + F2 (soumise au
    gating plafond/seuil de reprise) pour ce jour précis. Chaque jour est créé PUIS exécuté
    avant de passer au suivant — aucun process n'est pré-généré à l'avance.
    Un seul mail de synthèse (tableau récapitulatif par date) est envoyé à la fin, au lieu
    d'un mail par date traitée, et un seul fichier EMG + un seul fichier F2 (couvrant toute
    la période) sont envoyés au SFTP SOLIDIS, au lieu d'un fichier par date traitée.
    """
    processes = []
    results = []
    for d in _daterange(date_from, date_to):
        process, summary = _run_one_day(d)
        processes.append(process)
        results.append((d.isoformat(), summary))

    etl.notify_summary(date_from, date_to, results, retry=retry)
    etl.upload_declaration_files(date_from, date_to)
    return processes


def get_f2_declared_entries(date_from: str, date_to: str) -> list:
    sql = """
    SELECT [ID CREDIT] AS idcredit, [LOLOANID] AS lo_loan_id, [N° CIN] AS cin,
           [GENRE] AS genre, [AGENCE D'OCTROI] AS agence_octroi, [OBJET] AS objet,
           [CLASST] AS classt, [MONTANT] AS montant, [DATOUV] AS datouv,
           [DATECH] AS datech, [CYCLE] AS cycle, [TAUX] AS taux, [DATE_DECLARATION] AS date_declaration
    FROM [solidis].[dbo].[Solidis_f2_declared_v2]
    WHERE [DATE_DECLARATION] BETWEEN '{dateFrom}' AND '{dateTo}'
    ORDER BY [DATOUV]
    """.format(dateFrom=date_from, dateTo=date_to)
    df = pd.read_sql(sql, _get_conx())
    return df.to_dict('records') if not df.empty else []


def get_emg_summary(date_from: str, date_to: str) -> list:
    sql = """
    SELECT [reportDate], COUNT(*) AS nb_prets, SUM([Encours]) AS encours_total
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports]
    WHERE [reportDate] BETWEEN '{dateFrom}' AND '{dateTo}'
    GROUP BY [reportDate]
    ORDER BY [reportDate]
    """.format(dateFrom=date_from, dateTo=date_to)
    df = pd.read_sql(sql, _get_conx())
    return df.to_dict('records') if not df.empty else []
