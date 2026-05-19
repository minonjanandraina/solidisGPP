import os
import platform
import tempfile
from datetime import date

import pandas as pd
import paramiko
import pyodbc

from .models import ClientSituation, LoanRepaymentTransaction, ProcesseAppelDeGarantie


def _get_conx():
    driver = "ODBC Driver 17 for SQL Server" if platform.system() == "Linux" else "SQL Server"
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )


def _get_situation_clients(date_from: str, date_to: str) -> pd.DataFrame:
    sql = """
    SELECT
        r.[id]
        ,r.[IDCREDIT]
        ,r.[loLoanID]
        ,r.[Encours] * 0.5 as montantAppelGaranti
        ,r.[Encours]
        ,r.[DaysInArrears]
        ,r.[reportDate]
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports] r
    WHERE r.[DaysInArrears] = 61
    AND r.reportDate BETWEEN '{dateFrom}' AND '{dateTo}'
    """.format(dateFrom=date_from, dateTo=date_to)
    return pd.read_sql(sql, _get_conx())


def _get_loan_repayment_transactions(date_from: str, date_to: str) -> pd.DataFrame:
    sql = """
    SELECT
        r.[id]
        ,r.[IDCREDIT]
        ,r.[loLoanID]
        ,l.LoanAmountCurrent
        ,r.[Encours]
        ,r.[DaysInArrears]
        ,r.[reportDate]
        ,la.[DAte] as repaymentDate
        ,(case when lD.DebitType=2 then lA.AmountCRY else 0 end) as totalPaid
        ,la.loloanAllocationID as trx_id
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports] r
    join cbs.dbo.loLoan l on l.loLoanID = r.loLoanID
    join CBS.dbo.loloancredit lc on lc.loLoanId = l.loLoanID
    left join CBS.dbo.loloanAllocation lA on lA.loLoanCreditID = lc.loLoanCreditID
    left join CBS.dbo.loloanDebit lD on lD.loLoanDebitID = lA.loLoanDebitID
    WHERE r.[DaysInArrears] = 61
    AND lD.DebitType = 2
    AND r.[reportDate] >= la.[DAte]
    AND r.reportDate BETWEEN '{dateFrom}' AND '{dateTo}'
    """.format(dateFrom=date_from, dateTo=date_to)
    return pd.read_sql(sql, _get_conx())


def _upload_df_to_sftp(df: pd.DataFrame, remote_path: str, filename: str):
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
            raise Exception(f"Dossier SFTP introuvable : '{remote_path}'")
        sftp.put(temp_file, f"{remote_path}/{filename}")
        sftp.close()
        transport.close()
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def _filename(prefix: str, date_to: str) -> str:
    d = date_to.replace("-", "")
    return f"{prefix}_{d}.xlsx"


def lancer_appel(date_from: str, date_to: str) -> ProcesseAppelDeGarantie:
    # 1. Créer le process
    process = ProcesseAppelDeGarantie.objects.create(
        date_from=date_from,
        date_to=date_to,
        statut=ProcesseAppelDeGarantie.Statut.EN_COURS,
    )

    # 2. Situation clients à 61 jours
    df_situation = _get_situation_clients(date_from, date_to)
    if not df_situation.empty:
        ClientSituation.objects.bulk_create([
            ClientSituation(
                process=process,
                idcredit=row["IDCREDIT"],
                lo_loan_id=int(row["loLoanID"]),
                encours=row["Encours"],
                montant_appel_garanti=row["montantAppelGaranti"],
                days_in_arrears=int(row["DaysInArrears"]),
                report_date=row["reportDate"],
            )
            for _, row in df_situation.iterrows()
        ])

    # 3. Transactions de remboursement
    df_transactions = _get_loan_repayment_transactions(date_from, date_to)
    if not df_transactions.empty:
        LoanRepaymentTransaction.objects.bulk_create([
            LoanRepaymentTransaction(
                process=process,
                idcredit=row["IDCREDIT"],
                lo_loan_id=int(row["loLoanID"]),
                loan_amount_current=row["LoanAmountCurrent"],
                encours=row["Encours"],
                days_in_arrears=int(row["DaysInArrears"]),
                report_date=row["reportDate"],
                repayment_date=row["repaymentDate"],
                total_paid=row["totalPaid"],
                trx_id=row["trx_id"] if row["trx_id"] else None,
            )
            for _, row in df_transactions.iterrows()
        ])

    # 4. Upload SFTP
    remote_path = "/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/appel_en_garantie"
    if not df_situation.empty:
        _upload_df_to_sftp(
            df_situation,
            remote_path,
            _filename("PAMF_DIG_APPEL_SITUATION", date_to),
        )
    if not df_transactions.empty:
        _upload_df_to_sftp(
            df_transactions,
            remote_path,
            _filename("PAMF_DIG_APPEL_TRANSACTIONS", date_to),
        )

    # 5. Mise à jour statut
    process.statut = ProcesseAppelDeGarantie.Statut.SOUMIS
    process.save(update_fields=["statut"])

    return process
