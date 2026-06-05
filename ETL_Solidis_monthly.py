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
    "d.ravalison@pamf.mg",
    "n.ramiaramananjafy@pamf.mg",
    "s.andriamparany@pamf.mg",
    "m.razakasoa@pamf.mg",
    "k.rabenja@pamf.mg",
    "a.ralantoharivelo@pamf.mg",
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


def notify(date_from, date_to, case="success", retry=False):
    df = get_date(date_from)
    dt = get_date(date_to)

    if case == "success":
        if retry:
            subject = (
                f"SOLIDIS - PAMF - [RETRY] Déclaration du {df} au {dt}-rectificatif"
            )
        else:
            subject = f"SOLIDIS - PAMF - Déclaration du {df} au {dt}"
        recipients = _ALL

        message = f"L’envoi des fichiers est terminé pour la période du {df} au {dt}. Veuillez trouver  les fichiers dans les dossiers correspondants."
    elif case == "no_data":
        recipients = _INTERNAL
        subject = f"SOLIDIS - PAMF - [AVERTISSEMENT] Aucune donnée EMG {df} - {dt}"
        message = f"Aucune donnée EMG à envoyer pour la période du {df} au {dt}. Aucun fichier n’a été transmis à Solidis."
    elif case == "no_submissions":
        recipients = _INTERNAL
        subject = (
            f"SOLIDIS - PAMF - [AVERTISSEMENT] Aucune soumission éligible {df} - {dt}"
        )
        message = f"Aucune soumission initiale éligible pour la période du {df} au {dt}. Aucun fichier F2 n’a été transmis à Solidis."
    elif case == "delete_failure":
        recipients = _INTERNAL
        subject = f"SOLIDIS - PAMF - [ERREUR] Échec suppression {df} - {dt}"
        message = f"La suppression des données existantes a échoué pour la période du {df} au {dt}. L’envoi a été annulé pour éviter les doublons."
    else:
        return

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
        "sending mail......................................................................................."
    )
    send_email(to_address=recipients, subject=subject, body=body)


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
    con = pyodbc.connect(
        "DRIVER={SQL Server};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )
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


def get_emg_monthly(datefrom, dateto):
    con = pyodbc.connect(
        "DRIVER={SQL Server};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )
    sql = """
        DECLARE @datefrom DATE = '{}';
        DECLARE @dateto   DATE = '{}';
        
        -- Step 1: Generate daily dates ONLY within the requested window
        WITH DateSeries AS (
            -- Anchor: start at @datefrom
            SELECT
                l.loLoanID,
                l.AgreementDate,
                l.ClosingDate,
                l.MaturityDateCurrent,
                CAST(@datefrom AS DATE) AS reportDate        -- ← start from @datefrom
            FROM CBS.dbo.loLoan l
        	join [solidis].dbo.[Solidis_initial_loan_v2] il on il.LOLOANID = l.loLoanID
            WHERE  l.AgreementDate <= @dateto                 -- ← loan must have started before window ends
              AND ISNULL(l.ClosingDate, @dateto) >= @datefrom -- ← loan must not be closed before window starts
        
            UNION ALL
            -- Recursion: add one day until @dateto (or ClosingDate if earlier)
            SELECT
                d.loLoanID,
                d.AgreementDate,
                d.ClosingDate,
                d.MaturityDateCurrent,
                CAST(DATEADD(day, 1, d.reportDate) AS DATE)
            FROM DateSeries d
            WHERE DATEADD(day, 1, d.reportDate) <= 
                  CASE 
                      WHEN d.ClosingDate IS NULL THEN @dateto          -- open loan: go to @dateto
                      WHEN d.ClosingDate < @dateto THEN d.ClosingDate  -- closed before window end
                      ELSE @dateto                                      -- closed after window end
                  END
        ),
        
        -- Step 2: Latest balance per lb.[Date] (deduplicate)
        -- Step 2: Latest balance per lb.[Date] (deduplicate)
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
                    PARTITION BY lb.loLoanID, lb.[Date]
                    ORDER BY CASE WHEN lb.DateValidTo IS NULL THEN 0 ELSE 1 END ASC,
                             lb.DateValidTo DESC
                ) AS rn
            FROM CBS.dbo.loLoanBalanceOnDate lb
            join [solidis].dbo.[Solidis_initial_loan_v2] il on il.LOLOANID = lb.loLoanID
        )
        SELECT
            il.[ID CREDIT] as [IDCREDIT],
        
            CAST(il.[N° CIN] AS VARCHAR)                            AS [CIN],
        
            lb.PrincipalTotalCRY - lb.PrincipalPaidCRY
                - lb.PrincipalWoPaidCRY                             AS Encours,
        
            CASE WHEN lb.loStatus = 13 THEN 0
                ELSE
                    CASE WHEN DATEDIFF(day, ds.MaturityDateCurrent, ds.reportDate) < 0
                        THEN 0
                        ELSE DATEDIFF(day, ds.MaturityDateCurrent, ds.reportDate)
                    END
            END                                                     AS DaysInArrears,
            l.loanAmountCurrent,
            l.AgreementDate,
            l.ClosingDate,
            ds.MaturityDateCurrent,
            lb.[Date]                                               AS dateValidFrom,
            lb.DateValidTo,
            lb.loStatus                                             AS lostatus,
            l.loLoanID                                              AS loLoanID,
            ds.reportDate
        FROM DateSeries ds
        JOIN CBS.dbo.loLoan l  ON l.loLoanID = ds.loLoanID
        JOIN [solidis].dbo.[Solidis_initial_loan_v2] il  ON il.[LOLOANID] = l.loLoanID
        JOIN LatestBalance lb    ON  lb.loLoanID = ds.loLoanID  AND lb.rn = 1    
        														AND lb.[Date] = (        -- Carry forward: find the most recent balance on or before reportDate
        															SELECT MAX(lb2.[Date])
        															FROM CBS.dbo.loLoanBalanceOnDate lb2
        															WHERE lb2.loLoanID = ds.loLoanID
        															  AND lb2.[Date] <= ds.reportDate
        														)
        where 
            lb.PrincipalTotalCRY - lb.PrincipalPaidCRY - lb.PrincipalWoPaidCRY <> 0
            OR lb.loLoanBalanceOndateId = (
                SELECT MIN(lb3.loLoanBalanceOndateId)
                FROM CBS.dbo.loLoanBalanceOndate lb3
                WHERE lb3.loLoanID = ds.loLoanID
                  AND lb3.PrincipalTotalCRY - lb3.PrincipalPaidCRY - lb3.PrincipalWoPaidCRY = 0
            )
        
        ORDER BY ds.reportDate
        OPTION (MAXRECURSION 0);

    """.format(datefrom, dateto)
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


def main(date_from, date_to, retry=False):

    df_init_submition = get_init_submition(date_from, date_to)

    df_init_submition_to_send = generate_initial(df_init_submition, date_to)
    fn_f2 = generate_filename("PAMF_DIG F2 - monthly", date_to, "")

    df_emg = get_emg_monthly(date_from, date_to)
    df_emg = df_emg[
        ["IDCREDIT", "loLoanID", "CIN", "Encours", "DaysInArrears", "reportDate"]
    ]
    fn_emg = generate_filename("PAMF_DIG EMG - monthly", date_to, "")

    engine = getEngine()
    # before sending data to sql please delete between date_from and date_to to avoid duplicates in case of re-run
    # delete_Solidis_loan_update_monthly_reports(date_from,date_to)

    existing_update_deleted = delete_Solidis_loan_update_monthly_reports(
        date_from, date_to
    )
    """
    ┌──────────────────┬─────────────────────────────────┬─────────────────────────────────┐
    │       case       │           Recipients            │              When               │                                                                                                                                   
    ├──────────────────┼─────────────────────────────────┼─────────────────────────────────┤                                                                                                                                 
    │ 'success'        │ gpp@solidis.org + internal PAMF │ Upload completed normally       │                                                                                                                                 
    ├──────────────────┼─────────────────────────────────┼─────────────────────────────────┤
    │ 'no_data'        │ Internal PAMF only              │ df_emg is empty                 │
    ├──────────────────┼─────────────────────────────────┼─────────────────────────────────┤
    │ 'no_submissions' │ Internal PAMF only              │ df_init_submition_sent is empty │
    ├──────────────────┼─────────────────────────────────┼─────────────────────────────────┤
    │ 'delete_failure' │ Internal PAMF only              │ Delete step returned False      │
    └──────────────────┴─────────────────────────────────┴─────────────────────────────────┘
    """
    if existing_update_deleted:
        if len(df_emg) == 0:
            print("⚠️ No data to upload for the given date range.")
            notify(date_from, date_to, case="no_data")
        elif len(df_init_submition_to_send) == 0:
            print(
                "⚠️ No eligible initial submissions to upload for the given date range."
            )
            notify(date_from, date_to, case="no_submissions")
        else:
            df_emg = upload_df_to_sftp(
                df_emg,
                remote_path="/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/ENCOURS/",
                filename=fn_emg,
            )
            df_init_submition_to_send = upload_df_to_sftp(
                df_init_submition_to_send,
                remote_path="/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/F2/",
                filename=fn_f2,
            )
            df_init_submition_to_send.to_excel(fn_f2, index=False, engine="openpyxl")
            df_emg.to_excel(fn_emg, index=False, engine="openpyxl")
            df_emg.to_sql(
                name="Solidis_loan_update_monthly_reports",
                con=engine,
                if_exists="append",
                index=False,
            )
            notify(date_from, date_to, case="success", retry=retry)
    else:
        print("❌ Skipping upload to SQL due to delete failure")
        notify(date_from, date_to, case="delete_failure")


if __name__ == "__main__":
    check_system()
    # Example usage: main('2026-02-01', '2026-02-28')
    list_of_date_from_and_date_to = [
        ("2026-05-01", "2026-05-31"),
    ]
    for start_str_date, end_str_date in list_of_date_from_and_date_to:

        print("====================================================================================================")
        print(f"Processing data from {start_str_date} to {end_str_date}...")
        print("====================================================================================================")
        main(start_str_date, end_str_date, retry=True)
        print("====================================================================================================")
        print(f"Finished processing data from {start_str_date} to {end_str_date}.")
        print("====================================================================================================")
        print("|")
        print("|")
        print("|")
