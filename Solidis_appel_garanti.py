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


def getConx():
    # used to get data from solidis database
    if platform.system() == "Linux":
        con = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
        )
    else:
        con = pyodbc.connect(
            "DRIVER={SQL Server};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
        )
    return con


def getEngine():
    # used to update data in solidis database
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


def get_loan_repayment_transaction(date_from, date_to):
    # sql relever de compte
    sql_loan_repayment_transaction = """
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
    join cbs.dbo.loLoan l on l.loLoanID  = r.loLoanID
    join CBS.dbo.loloancredit lc on lc.loLoanId= l.loLoanID
    left join CBS.dbo.loloanAllocation lA on lA.loLoanCreditID=lc.loLoanCreditID
    left join CBS.dbo.loloanDebit lD on lD.loLoanDebitID=lA.loLoanDebitID
    where r.[DaysInArrears]=61 
    and lD.DebitType=2 and r.[reportDate]>=la.[DAte]
    and r.reportDAte between '{dateFrom}'  and '{dateTo}'  
    """.format(dateFrom=date_from, dateTo=date_to)
    df_repayment_transaction = pd.read_sql(sql_loan_repayment_transaction, getConx())
    return df_repayment_transaction


def get_situation_clients(date_from, date_to):
    # sql situation des clients en 61 jours d'arriérés
    sql_situation_clients = """
    SELECT 
        r.[id]
        ,r.[IDCREDIT]
        ,r.[loLoanID]
        ,r.[Encours] * 0.5 as montantAppelGaranti
        ,r.[DaysInArrears]
        ,r.[reportDate]

    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports] r

    where r.[DaysInArrears]=61 
    and r.reportDAte between '{dateFrom}'  and '{dateTo}' 

    """.format(dateFrom=date_from, dateTo=date_to)

    df_situation_clients = pd.read_sql(sql_situation_clients, getConx())

    return df_situation_clients


def main(date_from, date_to, retry=False):
    # step1: get data
    df_repayment_transaction = get_loan_repayment_transaction(date_from, date_to)
    df_situation_clients = get_situation_clients(date_from, date_to)

    # step2: update data in solidis database
    engine = getEngine()
    df_repayment_transaction.to_sql(
        "Solidis_loan_repayment_transaction",
        con=engine,
        if_exists="append",
        index=False,
    )
    df_situation_clients.to_sql(
        "Solidis_situation_clients", con=engine, if_exists="append", index=False
    )
