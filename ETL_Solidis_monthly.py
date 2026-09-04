# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 09:21:01 2026

@author: m.razakasoa
"""

import platform

import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text
import urllib
import paramiko
import tempfile
import os
from datetime import timedelta, date
from exchangelib import (
    Credentials,
    Account,
    Configuration,
    DELEGATE,
    Message,
    Mailbox,
    HTMLBody,
)
from datetime import datetime


def check_system():
    system = platform.system()
    available_drivers = pyodbc.drivers()
    required_driver = "ODBC Driver 17 for SQL Server" if system == "Linux" else "SQL Server"

    if required_driver not in available_drivers:
        raise EnvironmentError(
            f"Driver ODBC requis introuvable : '{required_driver}'\n"
            f"Drivers disponibles : {available_drivers}"
        )
    print(f"System check OK — Platform: {system}, Driver: '{required_driver}'")


def get_date(dt):
    dt_object = datetime.strptime(dt, "%Y-%m-%d")
    date_str = dt_object.strftime("%d/%m/%Y")
    return date_str


_INTERNAL = [
    #"d.ravalison@pamf.mg",
    #"n.ramiaramananjafy@pamf.mg",
    #"s.andriamparany@pamf.mg",
    "m.razakasoa@pamf.mg",
    #"k.rabenja@pamf.mg",
    #"a.ralantoharivelo@pamf.mg",
]
_ALL = [
    "gpp@solidis.org"
] + _INTERNAL  # just for testing, should be replace by 'gpp@solidis.org' later


def send_email(
    to_address, subject, body, cc_addresses=None, bcc_addresses=None, retry=False
):
    EMAIL_ADDRESS = "declaration.solidis@pamf.mg"
    USERNAME = "pamf\\declaration.solidis"
    PASSWORD = "S@l!d!$2025"
    SERVER = "mail.pamf.mg"

    try:
        credentials = Credentials(username=USERNAME, password=PASSWORD)
        config = Configuration(server=SERVER, credentials=credentials, auth_type="NTLM")
        account = Account(
            primary_smtp_address=EMAIL_ADDRESS,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )
        message = Message(
            account=account,
            subject=subject,
            body=HTMLBody(body),
            to_recipients=[
                Mailbox(email_address=addr)
                for addr in (
                    to_address if isinstance(to_address, list) else [to_address]
                )
            ],
        )
        if cc_addresses:
            message.cc_recipients = [
                Mailbox(email_address=addr)
                for addr in (
                    cc_addresses if isinstance(cc_addresses, list) else [cc_addresses]
                )
            ]
        if bcc_addresses:
            message.bcc_recipients = [
                Mailbox(email_address=addr)
                for addr in (
                    bcc_addresses
                    if isinstance(bcc_addresses, list)
                    else [bcc_addresses]
                )
            ]
        message.send()
        print(f"Email sent successfully to {to_address}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


_CASE_LABELS = {
    "success":         ("OK", "#137333", "#e6f4ea"),
    "f2_bloque":       ("F2 suspendu", "#c5221f", "#fce8e6"),
    "no_data":         ("Aucune donnée EMG", "#7a4900", "#fef0cd"),
    "no_submissions":  ("Aucune soumission F2", "#7a4900", "#fef0cd"),
    "delete_failure":  ("Échec suppression", "#c5221f", "#fce8e6"),
    None:              ("Échec", "#c5221f", "#fce8e6"),
}


def notify_summary(date_from, date_to, results, retry=False):
    """
    Envoie UN SEUL mail de synthèse (tableau récapitulatif par date) en fin de
    déclaration, plutôt qu'un mail par date traitée.

    results : liste de tuples (date_str, summary_dict | None) — un par date traitée,
    summary_dict étant celui retourné par main() (None en cas d'exception).
    """
    if not results:
        return

    df_label = get_date(date_from)
    dt_label = get_date(date_to)

    subject = f"SOLIDIS - PAMF - Synthèse déclaration du {df_label} au {dt_label}"
    if retry:
        subject = f"SOLIDIS - PAMF - [RETRY] {subject}"

    has_issue = any((s or {}).get("case") != "success" for _, s in results)

    rows_html = ""
    for day, s in results:
        s = s or {}
        case = s.get("case")
        label, color, bg = _CASE_LABELS.get(case, (case or "—", "#5f6368", "#f1f3f4"))
        rows_html += f"""
        <tr>
          <td style="padding:6px 10px; border:1px solid #e0e0e0;">{day}</td>
          <td style="padding:6px 10px; border:1px solid #e0e0e0;">
            <span style="background:{bg}; color:{color}; padding:2px 8px; border-radius:10px; font-size:12px; font-weight:600;">{label}</span>
          </td>
          <td style="padding:6px 10px; border:1px solid #e0e0e0; text-align:right;">{s.get('emg_lignes', 0)}</td>
          <td style="padding:6px 10px; border:1px solid #e0e0e0; text-align:right;">{s.get('f2_lignes', 0)}</td>
          <td style="padding:6px 10px; border:1px solid #e0e0e0; text-align:right;">{s.get('f2_lignes_exclues', 0)}</td>
        </tr>
        """

    table_html = f"""
    <table style="border-collapse:collapse; font-size:13px; width:100%;">
      <thead>
        <tr style="background:#f1f3f4;">
          <th style="padding:6px 10px; border:1px solid #e0e0e0; text-align:left;">Date</th>
          <th style="padding:6px 10px; border:1px solid #e0e0e0; text-align:left;">Statut</th>
          <th style="padding:6px 10px; border:1px solid #e0e0e0; text-align:right;">Lignes EMG</th>
          <th style="padding:6px 10px; border:1px solid #e0e0e0; text-align:right;">Lignes F2</th>
          <th style="padding:6px 10px; border:1px solid #e0e0e0; text-align:right;">F2 exclues</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    """

    message = (
        f"Synthèse de la déclaration du {df_label} au {dt_label} ({len(results)} date(s) traitée(s)) :"
        f"<br/><br/>{table_html}"
    )

    body = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333333; font-size: 14px; line-height: 1.5; margin:0; padding:0;">
    <div style="padding: 20px;">
      <p style="margin:0 0 10px 0;">Bonjour à tous,</p>
      <p style="margin:0 0 10px 0;">{message}</p>
      <p style="margin-top:20px; font-size:13px; color:#666666;">
        Cordialement,<br/>
        <em>Minonja</em>
      </p>
    </div>
    </body>
    </html>
    """.format(message=message)

    print(
        "sending summary mail......................................................................................."
    )
    send_email(to_address=_INTERNAL, subject=subject, body=body)
    return has_issue


def getEngine():
    server = "172.20.24.37"
    database = "solidis"
    username = "Minonja"
    password = "Minonja"
    if platform.system() == "Linux":
        connection_string = f"mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
        )
    else:
        connection_string = f"mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote(
            f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
        )
    # ODBC Driver 17 for SQL Server
    engine = create_engine(connection_string, use_setinputsizes=False)
    return engine


def get_pyodbc_connection():
    server = "172.20.24.37"
    database = "solidis"
    username = "Minonja"
    password = "Minonja"
    if platform.system() == "Linux":
        driver = "ODBC Driver 17 for SQL Server"
    else:
        driver = "SQL Server"
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
    )


def upload_df_to_sftp(df: pd.DataFrame, remote_path: str, filename: str):
    """
    Uploads a Pandas DataFrame to an SFTP server as an Excel file.

    Parameters:
        df (pd.DataFrame): DataFrame to upload.
        remote_path (str): Remote directory path on the SFTP server.
        filename (str): Name of the file to save (e.g., "data.xlsx").
    """
    # SFTP server credentials
    host = "34.209.31.76"
    port = 3434
    username = "pamf2"
    password = "TJLoRTlmAre@24"

    # Create a temporary file (cross-platform)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        temp_file = tmp.name
        # Save DataFrame to Excel
        df.to_excel(temp_file, index=False, engine="openpyxl")

    try:
        # Connect to the SFTP server
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Try changing to the remote directory
        try:
            sftp.chdir(remote_path)
        except IOError:
            raise Exception(f"Remote path '{remote_path}' does not exist.")

        # Upload the file
        remote_file_path = f"{remote_path}/{filename}"
        sftp.put(temp_file, remote_file_path)

        print(f"✅ Uploaded '{filename}' to '{remote_file_path}'")

        # Clean up
        sftp.close()
        transport.close()

    finally:
        # Delete temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
    return df


def check_gender(genderKYC, CIN):
    # genderKYC = 'Male'  #ou Female
    f_gender = 0
    is_ok = True
    if genderKYC == "Male":
        f_gender = 1
    if genderKYC == "Female":
        f_gender = 2
    gender = CIN[:6][5:]
    if str(gender) == str(f_gender):
        is_ok = True
    else:
        is_ok = False
    return is_ok


def get_init_submition(datefrom, dateto):
    con = get_pyodbc_connection()
    sql = """
    SELECT 
    	i.[ID CREDIT],i.[LOLOANID]
        ,i.[N° CIN]
        ,i.[DATE DE NAISSANCE]
        ,i.[GENRE]
        ,i.[AGENCE D'OCTROI]
        ,i.[OBJET]
        ,i.[CLASST]
        ,i.[MONTANT]
        ,convert(varchar,i.[DATOUV],23) as DATOUV
        ,i.[DATECH]
        ,i.[CYCLE]
        ,i.[TAUX], l.Status
    FROM [solidis].[dbo].[Solidis_initial_loan_v2] i
    join cbs.dbo.loLoan l on l.loLoanID = i.[LOLOANID]
    where
    convert(varchar,[DATOUV],23) between '{}' and '{}'
    and  l.Status in (4,5,13,10)

    """.format(datefrom, dateto)
    df = pd.read_sql(sql, con)
    df["DATE_DEBUT"] = datefrom
    df["DATE_FIN"] = dateto
    return df


def get_emg_monthly(report_date):
    """EMG d'une seule date (nous demandons désormais les EMG date par date)."""
    #pour les prêts clôturé, l'encours (lb.PrincipalTotalCRY - lb.PrincipalPaidCRY - lb.PrincipalWoPaidCRY) =0. et pour les prêts clôturé il faut au moin déclaré une seule fois (la date de clôturé) que l'encours =0. pour que le prêt clôturé ne soit pas pris en compte dans la déclaration EMG.
    # courrige le query dans get_emg_monthly en ce sens
    con = get_pyodbc_connection()
    sql = """
    DECLARE @reportDate DATE = '{}';

    WITH ActiveLoans AS (
        SELECT l.loLoanID
        FROM CBS.dbo.loLoan l
        WHERE l.AgreementDate <= @reportDate
          AND ISNULL(l.ClosingDate, @reportDate) >= @reportDate
          AND EXISTS (
              SELECT 1 FROM solidis.dbo.Solidis_f2_declared_v2 il
              WHERE il.LOLOANID = l.loLoanID
          )
    ),
    LatestBalance AS (
        SELECT
            lb.loLoanID,
            lb.loLoanBalanceOndateId,
            lb.[Date],
            lb.DateValidTo,
            lb.PrincipalTotalCRY,
            lb.PrincipalPaidCRY,
            lb.PrincipalWoPaidCRY,
            lb.loStatus,
            ROW_NUMBER() OVER (
                PARTITION BY lb.loLoanID
                ORDER BY lb.[Date] DESC,
                         CASE WHEN lb.DateValidTo IS NULL THEN 0 ELSE 1 END,
                         lb.DateValidTo DESC
            ) AS rn
        FROM CBS.dbo.loLoanBalanceOnDate lb
        WHERE lb.[Date] <= @reportDate
          AND EXISTS (SELECT 1 FROM ActiveLoans al WHERE al.loLoanID = lb.loLoanID)
    )
    SELECT
        il.[ID CREDIT] AS [IDCREDIT],
        CAST(il.[N° CIN] AS VARCHAR) AS [CIN],
        lb.PrincipalTotalCRY - lb.PrincipalPaidCRY - lb.PrincipalWoPaidCRY AS Encours,
        CASE
            WHEN lb.loStatus = 13 THEN 0
            ELSE CASE WHEN DATEDIFF(DAY, l.MaturityDateCurrent, @reportDate) < 0
                      THEN 0
                      ELSE DATEDIFF(DAY, l.MaturityDateCurrent, @reportDate)
                 END
        END AS DaysInArrears,
        l.loanAmountCurrent,
        l.AgreementDate,
        l.ClosingDate,
        l.MaturityDateCurrent,
        lb.[Date] AS dateValidFrom,
        lb.DateValidTo,
        lb.loStatus,
        l.loLoanID,
        @reportDate AS reportDate
    FROM LatestBalance lb
    JOIN CBS.dbo.loLoan l
        ON l.loLoanID = lb.loLoanID
    JOIN solidis.dbo.Solidis_f2_declared_v2 il
        ON il.LOLOANID = lb.loLoanID
    LEFT JOIN [solidis].[dbo].[Solidis_loan_update_monthly_reports] re
        ON re.loLoanID = il.LOLOANID AND re.Encours = 0 
    WHERE lb.rn = 1
      
      AND re.loLoanID IS NULL and l.AgreementDate<= @reportDate;
    """.format(report_date)
    df = pd.read_sql(sql, con)

    return df


def generate_filename(fn, date_str, error):
    # Calcule la date d’hier

    # Formate la date au format JJMMYYYY

    # Construit le nom de fichier complet
    filename = f"{fn}{date_str}{error}.xlsx"

    return filename


def generate_initial(df_init, dt):
    dt = dt.replace("-", "")
    df_init["LOLOANID"] = pd.to_numeric(df_init["LOLOANID"], errors="coerce").astype(
        "Int64"
    )

    df_init["is_eligible"] = df_init.apply(
        lambda row: check_gender(row["GENRE"], str(row["N° CIN"])), axis=1
    )
    df_init_ok = df_init[df_init["is_eligible"] == True]
    df_init_ko = df_init[df_init["is_eligible"] == False]

    engine = getEngine()
    if len(df_init_ko) > 0:
        df_init_ko.to_sql(
            name="Solidis_loan_KYC_KO_new", con=engine, if_exists="append", index=False
        )
    return df_init_ok


def delete_Solidis_loan_update_monthly_reports(date_from, date_to):
    engine = getEngine()
    try:
        with engine.connect() as connection:
            delete_query = """DELETE FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports]  WHERE reportDate BETWEEN '{}' AND '{}'""".format(
                date_from, date_to
            )
            connection.execute(text(delete_query))
            print(
                f"✅ Deleted records from Solidis_loan_update_monthly_reports where reportDate between {date_from} and {date_to}"
            )
            connection.commit()
            return True
    except Exception as e:
        print(f"❌ Error deleting records: {e}")
        return False


def delete_Solidis_f2_declared_v2(date_from, date_to):
    """Supprime les F2 déjà déclarés sur la période avant réinsertion (évite les doublons en cas de re-run)."""
    engine = getEngine()
    try:
        with engine.connect() as connection:
            delete_query = """DELETE FROM [solidis].[dbo].[Solidis_f2_declared_v2]  WHERE DATE_DECLARATION BETWEEN '{}' AND '{}'""".format(
                date_from, date_to
            )
            connection.execute(text(delete_query))
            print(
                f"✅ Deleted records from Solidis_f2_declared_v2 where DATE_DECLARATION between {date_from} and {date_to}"
            )
            connection.commit()
            return True
    except Exception as e:
        print(f"❌ Error deleting records: {e}")
        return False


def ensure_declaration_tables():
    """Crée (si besoin) les tables de configuration de la déclaration et de suivi des entrées F2."""
    engine = getEngine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
        IF OBJECT_ID('solidis.dbo.Solidis_declaration_config', 'U') IS NULL
        CREATE TABLE [solidis].[dbo].[Solidis_declaration_config] (
            [id] int IDENTITY(1,1) PRIMARY KEY,
            [plafond_emg] decimal(18,2) NOT NULL DEFAULT 5000000000,
            [seuil_reprise_pct] decimal(5,4) NOT NULL DEFAULT 0.80,
            [f2_bloque] bit NOT NULL DEFAULT 0,
            [updated_at] datetime NOT NULL DEFAULT GETDATE()
        )
        """
            )
        )
        connection.execute(
            text(
                """
        IF NOT EXISTS (SELECT 1 FROM [solidis].[dbo].[Solidis_declaration_config])
        INSERT INTO [solidis].[dbo].[Solidis_declaration_config] (plafond_emg, seuil_reprise_pct, f2_bloque)
        VALUES (5000000000, 0.80, 0)
        """
            )
        )
        connection.execute(
            text(
                """
        IF OBJECT_ID('solidis.dbo.Solidis_f2_declared_v2', 'U') IS NULL
        CREATE TABLE [solidis].[dbo].[Solidis_f2_declared_v2] (
            [ID] int IDENTITY(1,1) PRIMARY KEY,
            [LOLOANID] float NULL,
            [REF] varchar(100) NULL,
            [ID CREDIT] varchar(100) NULL,
            [N° CIN] bigint NULL,
            [DATE DE NAISSANCE] varchar(50) NULL,
            [GENRE] varchar(20) NULL,
            [AGENCE D'OCTROI] varchar(200) NULL,
            [OBJET] varchar(200) NULL,
            [CLASST] varchar(100) NULL,
            [MONTANT] bigint NULL,
            [DATOUV] date NULL,
            [DATECH] date NULL,
            [CYCLE] bigint NULL,
            [TAUX] float NULL,
            [DATE_DECLARATION] date NULL
        )
        """
            )
        )


def get_declaration_config():
    """Lit le plafond EMG, le seuil de reprise et l'état de blocage F2 courant (dynamique, éditable via le web)."""
    ensure_declaration_tables()
    engine = getEngine()
    df = pd.read_sql(
        "SELECT TOP 1 * FROM [solidis].[dbo].[Solidis_declaration_config] ORDER BY id",
        engine,
    )
    row = df.iloc[0]
    return {
        "plafond_emg": float(row["plafond_emg"]),
        "seuil_reprise_pct": float(row["seuil_reprise_pct"]),
        "f2_bloque": bool(row["f2_bloque"]),
    }


def update_f2_bloque(new_state: bool):
    engine = getEngine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE [solidis].[dbo].[Solidis_declaration_config] "
                "SET f2_bloque = :state, updated_at = GETDATE()"
            ),
            {"state": new_state},
        )


def get_encours_reference(date_from):
    """Encours total (toutes lignes) à la dernière reportDate connue avant date_from — sert de référence au gating F2."""
    engine = getEngine()
    sql = """
    SELECT SUM(Encours) AS encours
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports]
    WHERE reportDate = (
        SELECT MAX(reportDate)
        FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports]
        WHERE reportDate < '{date_from}'
    )
    """.format(date_from=date_from)
    df = pd.read_sql(sql, engine)
    value = df.iloc[0]["encours"]
    return float(value) if value is not None else None


def build_f2_daily_states(date_from, date_to, df_emg, config):
    """
    Détermine, pour CHAQUE date entre date_from et date_to, si le statut est
    'remplissage' (F2 autorisé) ou 'stop' (F2 suspendu) — hystérésis évaluée jour par
    jour à partir de l'encours de la veille (j-1) dans Solidis_loan_update_monthly_reports :
      - statut 'remplissage' et encours(j-1) > plafond            -> passe 'stop'
      - statut 'stop'        et encours(j-1) <= seuil_reprise     -> passe 'remplissage'
      - sinon le statut de la veille est conservé
    Sans donnée d'encours pour j-1, le statut courant est conservé (pas de bascule à l'aveugle).

    Retourne (states, f2_bloque_fin_periode) où states est un dict {date: bool bloqué}.
    """
    plafond = config["plafond_emg"]
    seuil_reprise = plafond * config["seuil_reprise_pct"]
    bloque = config["f2_bloque"]

    encours_by_day = (
        df_emg.assign(_day=pd.to_datetime(df_emg["reportDate"]).dt.date)
        .groupby("_day")["Encours"].sum()
        .to_dict()
    )

    date_from_d = pd.to_datetime(date_from).date()
    date_to_d = pd.to_datetime(date_to).date()

    encours_prev = get_encours_reference(date_from)

    states = {}
    current_day = date_from_d
    while current_day <= date_to_d:
        if encours_prev is not None:
            if not bloque and encours_prev > plafond:
                bloque = True
            elif bloque and encours_prev <= seuil_reprise:
                bloque = False
        states[current_day] = bloque
        encours_prev = encours_by_day.get(current_day)
        current_day += timedelta(days=1)

    return states, bloque


def filter_f2_by_daily_state(df_init_submition_to_send, daily_states):
    """Ne garde que les lignes F2 dont le DATOUV tombe un jour 'remplissage' (F2 autorisé)."""
    df = df_init_submition_to_send.copy()
    datouv_day = pd.to_datetime(df["DATOUV"]).dt.date
    actif = datouv_day.map(lambda d: not daily_states.get(d, True))
    return df[actif].reset_index(drop=True), df[~actif].reset_index(drop=True)


def save_f2_declared(df_init_submition_to_send, date_to, engine):
    """Enregistre les entrées F2 effectivement déclarées (même structure que Solidis_initial_loan_v2)."""
    cols = [
        "LOLOANID", "REF", "ID CREDIT", "N° CIN", "DATE DE NAISSANCE", "GENRE",
        "AGENCE D'OCTROI", "OBJET", "CLASST", "MONTANT", "DATOUV", "DATECH", "CYCLE", "TAUX",
    ]
    df = df_init_submition_to_send.copy()
    if "REF" not in df.columns:
        df["REF"] = None
    df = df[cols]
    df["DATE_DECLARATION"] = date_to
    df.to_sql(name="Solidis_f2_declared_v2", con=engine, if_exists="append", index=False)


def upload_declaration_files(date_from, date_to):
    """
    Envoie UN SEUL fichier EMG et UN SEUL fichier F2 pour toute la période
    [date_from, date_to] vers le SFTP SOLIDIS — au lieu d'un fichier par date traitée.
    Relit les données déjà écrites en base par main() pour chaque jour de la période.
    """
    engine = getEngine()

    sql_emg = """
    SELECT [IDCREDIT], [loLoanID], [CIN], [Encours], [DaysInArrears], [reportDate]
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports]
    WHERE [reportDate] BETWEEN '{}' AND '{}'
    ORDER BY [reportDate], [loLoanID]
    """.format(date_from, date_to)
    df_emg = pd.read_sql(sql_emg, engine)

    sql_f2 = """
    SELECT [LOLOANID], [REF], [ID CREDIT], [N° CIN], [DATE DE NAISSANCE], [GENRE],
           [AGENCE D'OCTROI], [OBJET], [CLASST], [MONTANT], [DATOUV], [DATECH], [CYCLE], [TAUX]
    FROM [solidis].[dbo].[Solidis_f2_declared_v2]
    WHERE [DATE_DECLARATION] BETWEEN '{}' AND '{}'
    ORDER BY [DATOUV]
    """.format(date_from, date_to)
    df_f2 = pd.read_sql(sql_f2, engine)

    fn_emg = generate_filename("PAMF_DIG EMG - monthly", date_to, "")
    fn_f2 = generate_filename("PAMF_DIG F2 - monthly", date_to, "")

    if not df_emg.empty:
        df_emg.to_excel(fn_emg, index=False, engine="openpyxl")
        upload_df_to_sftp(
            df_emg,
            remote_path="/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/ENCOURS/",
            filename=fn_emg,
        )
    if not df_f2.empty:
        df_f2.to_excel(fn_f2, index=False, engine="openpyxl")
        upload_df_to_sftp(
            df_f2,
            remote_path="/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/F2/",
            filename=fn_f2,
        )

    return df_emg, df_f2


def main(date_from, date_to):

    engine = getEngine()

    config = get_declaration_config()

    summary = {
        "case": None,
        "f2_bloque": config["f2_bloque"],
        "emg_lignes": 0,
        "emg_encours_total": 0,
        "f2_lignes": 0,
        "f2_lignes_exclues": 0,
        "jours_f2_actifs": 0,
        "jours_f2_bloques": 0,
    }

    # --- 1) Déclaration F2, calculée et ENREGISTRÉE AVANT l'EMG ---------------------------
    # get_emg_monthly() ne retient que les prêts déjà présents dans Solidis_f2_declared_v2
    # (EXISTS ...). Si l'EMG du jour était calculé avant l'insertion du F2 du jour même,
    # les prêts entrés en portefeuille ce jour-là étaient absents de leur propre encours du
    # jour (ex : F2 du 31/07 non repris dans l'EMG du 31/07). On déclare donc le F2 d'abord.
    #
    # Le gating (build_f2_daily_states) ne dépend que de l'encours de la veille déjà
    # persisté (get_encours_reference), jamais de l'EMG du jour lui-même : df_emg n'y sert
    # qu'à faire progresser l'hystérésis sur les jours SUIVANTS d'un même appel — inutilisé
    # ici puisque main() est toujours appelé jour par jour (date_from == date_to).
    daily_states, f2_bloque_fin = build_f2_daily_states(
        date_from, date_to, pd.DataFrame(columns=["Encours", "reportDate"]), config
    )
    if f2_bloque_fin != config["f2_bloque"]:
        update_f2_bloque(f2_bloque_fin)

    jours_actifs = sum(1 for bloque in daily_states.values() if not bloque)
    jours_bloques = len(daily_states) - jours_actifs
    summary["f2_bloque"] = f2_bloque_fin
    summary["jours_f2_actifs"] = jours_actifs
    summary["jours_f2_bloques"] = jours_bloques

    if jours_actifs == 0:
        print(
            f"⏸️ Déclaration F2 suspendue sur toute la période {date_from} → {date_to} "
            f"(encours au-dessus du seuil de reprise chaque jour)."
        )
        f2_case = "f2_bloque"
    else:
        df_init_submition = get_init_submition(date_from, date_to)
        df_init_submition_to_send = generate_initial(df_init_submition, date_to)
        fn_f2 = generate_filename("PAMF_DIG F2 - monthly", date_to, "")

        if len(df_init_submition_to_send) == 0:
            print("⚠️ No eligible initial submissions to upload for the given date range.")
            f2_case = "no_submissions"
        else:
            df_f2_actif, df_f2_exclu = filter_f2_by_daily_state(df_init_submition_to_send, daily_states)
            summary["f2_lignes_exclues"] = int(len(df_f2_exclu))

            if len(df_f2_actif) == 0:
                print(
                    f"⏸️ {len(df_f2_exclu)} entrée(s) F2 tombent un jour bloqué sur la période "
                    f"{date_from} → {date_to} : aucune déclaration F2 ce run."
                )
                f2_case = "f2_bloque"
            else:
                # avant d'insérer, supprimer les F2 déjà déclarés sur la période pour éviter les doublons
                existing_f2_deleted = delete_Solidis_f2_declared_v2(date_from, date_to)
                if not existing_f2_deleted:
                    print("❌ Skipping F2 upload to SQL due to delete failure")
                    f2_case = "delete_failure"
                else:
                    df_f2_actif.to_excel(fn_f2, index=False, engine="openpyxl")
                    save_f2_declared(df_f2_actif, date_to, engine)
                    summary["f2_lignes"] = int(len(df_f2_actif))
                    f2_case = "success"
                    if jours_bloques:
                        print(
                            f"ℹ️ {jours_bloques} jour(s) bloqué(s) sur la période : "
                            f"{len(df_f2_exclu)} entrée(s) F2 non déclarée(s) ce run."
                        )

    # --- 2) EMG : toujours calculé et envoyé, même si F2 est suspendu (comme avant) --------
    # Calculé maintenant APRÈS la déclaration F2 ci-dessus, pour que les prêts tout juste
    # insérés dans Solidis_f2_declared_v2 soient bien inclus dans l'encours du jour.
    df_emg = get_emg_monthly(date_to)
    df_emg = df_emg[
        ["IDCREDIT", "loLoanID", "CIN", "Encours", "DaysInArrears", "reportDate"]
    ]
    fn_emg = generate_filename("PAMF_DIG EMG - monthly", date_to, "")

    # before sending data to sql please delete between date_from and date_to to avoid duplicates in case of re-run
    existing_update_deleted = delete_Solidis_loan_update_monthly_reports(
        date_from, date_to
    )
    # Pas de mail par déclaration : le "case" est renvoyé dans summary et agrégé
    # dans un mail de synthèse unique par notify_summary() en fin de traitement.
    if not existing_update_deleted:
        print("❌ Skipping upload to SQL due to delete failure")
        summary["case"] = "delete_failure"
        return summary

    if len(df_emg) == 0:
        print("⚠️ No data to upload for the given date range.")
        summary["case"] = "no_data"
        return summary

    df_emg.to_excel(fn_emg, index=False, engine="openpyxl")
    df_emg.to_sql(
        name="Solidis_loan_update_monthly_reports",
        con=engine,
        if_exists="append",
        index=False,
    )
    summary["emg_lignes"] = int(len(df_emg))
    summary["emg_encours_total"] = float(
        df_emg.loc[df_emg["reportDate"] == df_emg["reportDate"].max(), "Encours"].sum()
    )

    summary["case"] = f2_case
    return summary


if __name__ == "__main__":
    check_system()
    # Example usage: main('2026-02-01', '2026-02-28')
    list_of_date_from_and_date_to = [
        ("2026-06-01", "2026-06-30"),
    ]
    for start_str_date, end_str_date in list_of_date_from_and_date_to:

        print("====================================================================================================")
        print(f"Processing data from {start_str_date} to {end_str_date}...")
        print("====================================================================================================")

        # Un mail par déclaration -> un seul mail de synthèse en fin de traitement.
        results = []
        d = datetime.strptime(start_str_date, "%Y-%m-%d").date()
        d_end = datetime.strptime(end_str_date, "%Y-%m-%d").date()
        while d <= d_end:
            d_str = d.isoformat()
            try:
                summary = main(d_str, d_str)
            except Exception as exc:
                print(f"❌ Erreur lors du traitement du {d_str} : {exc}")
                summary = None
            results.append((d_str, summary))
            d += timedelta(days=1)

        notify_summary(start_str_date, end_str_date, results, retry=True)

        # Un seul fichier EMG + un seul fichier F2 pour toute la période vers le SFTP,
        # plutôt qu'un fichier par date traitée.
        upload_declaration_files(start_str_date, end_str_date)

        print("====================================================================================================")
        print(f"Finished processing data from {start_str_date} to {end_str_date}.")
        print("====================================================================================================")
        print("|")
        print("|")
        print("|")
