# -*- coding: utf-8 -*-
"""
Created on Thu Jan 22 08:48:02 2026

@author: m.razakasoa
"""

#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import pyodbc
from sqlalchemy import create_engine
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


def getEngine():
    server = "172.20.24.37"
    database = "solidis"
    username = "Minonja"
    password = "Minonja"

    connection_string = f"mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote(
        f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
    )
    engine = create_engine(connection_string, use_setinputsizes=False)
    return engine


def delete_solidis_loans(insert_date):
    """
    Delete records from:
    - Solidis_loan_closed
    - Solidis_loan_update
    where insertDate >= insert_date
    """

    conn = pyodbc.connect(
        "DRIVER={SQL Server};"
        "SERVER=172.20.24.37;"
        "DATABASE=solidis;"
        "UID=Minonja;"
        "PWD=Minonja;"
    )

    try:
        cursor = conn.cursor()

        sql_closed = """
        DELETE FROM [solidis].[dbo].[Solidis_loan_closed]
        WHERE insertDate >= ?
        """

        sql_update = """
        DELETE FROM [solidis].[dbo].[Solidis_loan_update]
        WHERE insertDate >= ?
        """

        cursor.execute(sql_closed, insert_date)
        deleted_closed = cursor.rowcount

        cursor.execute(sql_update, insert_date)
        deleted_update = cursor.rowcount

        conn.commit()

        print(
            f"✅ Delete OK | "
            f"Closed: {deleted_closed} rows | "
            f"Update: {deleted_update} rows"
        )

    except Exception as e:
        conn.rollback()
        print("❌ Error during delete:", e)

    finally:
        cursor.close()
        conn.close()


def generate_filename(fn, dt, error):
    # Calcule la date d’hier

    # Formate la date au format JJMMYYYY
    date_str = dt.strftime("%d%m%Y")

    # Construit le nom de fichier complet
    filename = f"{fn}{date_str}{error}.xlsx"

    return filename


def get_date(date):
    # Calcule la date d’hier

    # Formate la date au format JJMMYYYY
    date_str = date.strftime("%d%m%Y")

    # Construit le nom de fichier complet

    return date_str


def get_init_submition(date_declaration):
    con = pyodbc.connect(
        "DRIVER={SQL Server};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )
    sql = """
    SELECT  [ID CREDIT],[LOLOANID]
      ,[N° CIN]
      ,[DATE DE NAISSANCE]
      ,[GENRE]
      ,[AGENCE D'OCTROI]
      ,[OBJET]
      ,[CLASST]
      ,[MONTANT]
      ,convert(varchar,[DATOUV],23) as DATOUV
      ,[DATECH]
      ,[CYCLE]
      ,[TAUX]
    FROM [solidis].[dbo].[Solidis_initial_loan] 
    where  convert(varchar,[DATOUV],23) = '{}'and [AGENCE D'OCTROI]='Digital'

    """.format(date_declaration)
    df = pd.read_sql(sql, con)
    return df


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
    """
    f_gender  = 0
    is_ok = True
    if genderKYC == 'Male':
        f_gender = 1
    if genderKYC == 'Female':
        f_gender = 2
    gender = CIN[:6][5:]
    if str(gender) == str(f_gender):
        is_ok = True
    else:
        is_ok = False

    """
    if str(CIN[:6][5:]) in ("1", "2"):
        return True
    elif CIN == "312020051093":
        return True
    else:
        return False


def send_email(to_address, subject, body, cc_addresses=None, bcc_addresses=None):
    # Mail server parameters
    EMAIL_ADDRESS = "declaration.solidis@pamf.mg"
    USERNAME = "pamf\\declaration.solidis"  # Domain\username format
    PASSWORD = "S@l!d!$2025"  # Replace with actual password
    SERVER = "mail.pamf.mg"

    try:
        # Set up credentials
        credentials = Credentials(username=USERNAME, password=PASSWORD)

        # Configure the Exchange connection
        config = Configuration(
            server=SERVER,
            credentials=credentials,
            auth_type="NTLM",  # Typical for Exchange with domain auth
        )

        # Connect to the account
        account = Account(
            primary_smtp_address=EMAIL_ADDRESS,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )

        # Create the message
        message = Message(
            account=account,
            subject=subject,
            body=HTMLBody(body),
            to_recipients=[
                Mailbox(email_address=addr)
                for addr in (to_address if isinstance(to_address, list) else to_address)
            ],
        )

        # Add CC recipients if provided
        if cc_addresses:
            message.cc_recipients = [
                Mailbox(email_address=addr)
                for addr in (
                    cc_addresses if isinstance(cc_addresses, list) else [cc_addresses]
                )
            ]

        # Add BCC recipients if provided
        if bcc_addresses:
            message.bcc_recipients = [
                Mailbox(email_address=addr)
                for addr in (
                    bcc_addresses
                    if isinstance(bcc_addresses, list)
                    else [bcc_addresses]
                )
            ]

        # Send the message
        message.send()
        print(f"Email sent successfully to {to_address}")
        return True

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def notify(date):
    mailBody = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333333; font-size: 14px; line-height: 1.5; margin:0; padding:0;">
    <div style="padding: 20px;">
      <p style="margin:0 0 10px 0;">Bonjour à tous,</p>
      <p style="margin:0 0 10px 0;">
    L’envoi des fichiers est terminé pour la date du {date}
      <p style="margin-top:20px; font-size:13px; color:#666666;">
        Cordialement,<br/>
        <em>Minonja</em>
      </p>
    </div>
    </body>
    </html>


    """.format(date=get_date(date))
    # Send a test email
    print(
        "sending mail......................................................................................."
    )

    try:
        send_email(
            to_address=[
                "gpp@solidis.org",
                "d.ravalison@pamf.mg",
                "n.ramiaramananjafy@pamf.mg",
                "s.andriamparany@pamf.mg",
                "m.razakasoa@pamf.mg",
                "k.rabenja@pamf.mg",
                "z.andriamanamihaga@pamf.mg",
            ],
            subject="SOLIDIS - PAMF - Déclaration du {} -rectification ".format(
                get_date(date)
            ),
            body=mailBody,
        )

    except Exception as e:
        print("Error sending email:", e)


def send_report(dt):

    insertDate = dt + timedelta(days=1)

    date_str = dt.strftime("%Y-%m-%d")
    insertDate_str = insertDate.strftime("%Y-%m-%d")

    df = get_init_submition(date_str)
    if len(df) > 0:
        engine = getEngine()
        delete_solidis_loans(insertDate_str)
        print("*" * 50)
        print(date_str)
        print("*" * 50)
        df["is_ok"] = df.apply(
            lambda row: check_gender(row["GENRE"], str(row["N° CIN"])), axis=1
        )
        df_ok = df[df["is_ok"] == True]
        df_ko = df[df["is_ok"] == False]

        list_col = [
            "ID CREDIT",
            "LOLOANID",
            "N° CIN",
            "DATE DE NAISSANCE",
            "GENRE",
            "AGENCE D'OCTROI",
            "OBJET",
            "CLASST",
            "MONTANT",
            "DATOUV",
            "DATECH",
            "CYCLE",
            "TAUX",
        ]
        list_col_ko = [
            "ID CREDIT",
            "N° CIN",
            "DATE DE NAISSANCE",
            "GENRE",
            "AGENCE D'OCTROI",
            "OBJET",
            "CLASST",
            "MONTANT",
            "DATOUV",
            "DATECH",
            "CYCLE",
            "TAUX",
        ]
        df_ok = df_ok[list_col]
        df_ko = df_ko[list_col_ko]
        for col in ["DATOUV", "DATECH"]:
            df_ok[col] = df_ok[col].astype(str).str[:10]
        df_ok = upload_df_to_sftp(
            df_ok,
            remote_path="/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/F2/",
            filename=generate_filename("PAMF_DIG F2 ", dt, ""),
        )
        # df_ko=upload_df_to_sftp(df_ko, remote_path='/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/F2/', filename=generate_filename("PAMF_DIG F2 ", "__gender_error__"))
        df_ok.to_sql(
            name="test_init_loan_ok", con=engine, if_exists="append", index=False
        )

        df_ok.to_excel(generate_filename("PAMF_DIG F2 ", dt, ""))
        df_ko.to_excel(generate_filename("PAMF_DIG F2 ", dt, "__gender_error__"))
        df_ko.to_sql(
            name="Solidis_loan_KYC_KO", con=engine, if_exists="append", index=False
        )

    con = pyodbc.connect(
        "DRIVER={SQL Server};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja"
    )
    sql = """
    SELECT 
        il.[ID CREDIT], 
    	cast(il.[N° CIN] as varchar) as [N° CIN] ,
    	lb.PrincipalTotalCRY - lb.PrincipalPaidCRY - lb.PrincipalWoCRY as Encours ,
    	case when lb.loStatus = 13 then 0 
    		 else 
    			case when datediff(day,l.MaturityDateCurrent,'{d}') <0 
    				 then 0 
    				 else datediff(day,l.MaturityDateCurrent,'{d}')  
    			end  
    	end as DaysInArrears,
        l.loanAmountCurrent, 
    	l.AgreementDate,
    	l.ClosingDate,
    	l.MaturityDateCurrent,'{insertdate}' as InsertDAte,
    
    	l.Status,l.[loLoanID] as LOLOANID
    FROM [solidis].dbo.[Solidis_initial_loan] il
    JOIN CBS.dbo.loLoan l  ON l.loLoanID  = il.[LOLOANID] 
    join CBS.dbo.loLoanBalanceOnDate lb on lb.loLoanID=l.loLoanID
    left join [solidis].dbo.[Solidis_loan_closed] ilc on ilc.[ID CREDIT] =il.[ID CREDIT]
    
    where '{d}' between lb.[Date] and  ISNULL(lb.DateValidTo,'{d}')
    
    
    and ilc.[ID CREDIT] is null
    
    
    """.format(d=date_str, insertdate=insertDate_str)
    print(sql)
    df_update = pd.read_sql(sql, con)

    df_update = df_update[
        ["ID CREDIT", "LOLOANID", "N° CIN", "Encours", "DaysInArrears", "InsertDAte"]
    ]
    fn = generate_filename("PAMF_DIG EMG ", dt, "")

    df_update = upload_df_to_sftp(
        df_update,
        remote_path="/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/ENCOURS/",
        filename=fn,
    )
    print(fn)

    engine = getEngine()
    df_update.to_sql(
        name="Solidis_loan_update", con=engine, if_exists="append", index=False
    )
    df_closed = df_update[df_update["Encours"] == 0]

    df_closed = df_closed[
        ["ID CREDIT", "N° CIN", "Encours", "DaysInArrears", "InsertDAte"]
    ]
    df_closed.to_sql(
        name="Solidis_loan_closed", con=engine, if_exists="append", index=False
    )

    # notify(dt)


# Example usage

liste_date = [
    date(2026, 1, 16),
    date(2026, 1, 17),
    date(2026, 1, 18),
    date(2026, 1, 19),
    date(2026, 1, 20),
    date(2026, 1, 21),
    date(2026, 1, 22),
    date(2026, 1, 23),
    date(2026, 1, 24),
    date(2026, 1, 25),
    date(2026, 1, 26),
    date(2026, 1, 27),
    date(2026, 1, 28),
    date(2026, 1, 29),
    date(2026, 1, 30),
    date(2026, 1, 31),
]

for d in liste_date:

    send_report(d)

'''
dt=date(2026,1,18)
insertDate = dt + timedelta(days=1)

date_str = dt.strftime("%Y-%m-%d")
insertDate_str = insertDate.strftime("%Y-%m-%d")


df = get_init_submition(date_str)
if len(df)>0:
    delete_solidis_loans(insertDate_str)
    print('fffffffffffffffffffffffffff')
    print('fffffffffffffffffffffffffff')
    print(len(df))
    print('fffffffffffffffffffffffffff')
    print('fffffffffffffffffffffffffff')
    df['is_ok'] = df.apply(lambda row: check_gender(row['GENRE'], str(row['N° CIN'])), axis=1)
    df_ok=df[df['is_ok'] == True]
    df_ko=df[df['is_ok'] == False]
    
    list_col=['ID CREDIT','LOLOANID', 'N° CIN', 'DATE DE NAISSANCE', 'GENRE',
           'AGENCE D\'OCTROI', 'OBJET', 'CLASST', 'MONTANT', 'DATOUV', 'DATECH',
           'CYCLE', 'TAUX']
    list_col_ko=['ID CREDIT', 'N° CIN', 'DATE DE NAISSANCE', 'GENRE',
           'AGENCE D\'OCTROI', 'OBJET', 'CLASST', 'MONTANT', 'DATOUV', 'DATECH',
           'CYCLE', 'TAUX']
    df_ok=df_ok[list_col]
    df_ko=df_ko[list_col_ko]
    df_ok=upload_df_to_sftp(df_ok, remote_path='/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/F2/', filename=generate_filename("PAMF_DIG F2 ",dt,""))
    #df_ko=upload_df_to_sftp(df_ko, remote_path='/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/F2/', filename=generate_filename("PAMF_DIG F2 ", "__gender_error__"))
    engine = getEngine()
    df_ko.to_excel('df_ko.xlsx')
    df_ko.to_sql(name='Solidis_loan_KYC_KO',
                            con=engine,
                            if_exists='append',
                            index=False)

con  = pyodbc.connect('DRIVER={SQL Server};SERVER=172.20.24.37;DATABASE=solidis;UID=Minonja;PWD=Minonja')
sql="""
SELECT 
    il.[ID CREDIT], 
	cast(il.[N° CIN] as varchar) as [N° CIN] ,
	lb.PrincipalTotalCRY - lb.PrincipalPaidCRY - lb.PrincipalWoCRY as Encours ,
	case when lb.loStatus = 13 then 0 
		 else 
			case when datediff(day,l.MaturityDateCurrent,'{d}') <0 
				 then 0 
				 else datediff(day,l.MaturityDateCurrent,'{d}')  
			end  
	end as DaysInArrears,
    l.loanAmountCurrent, 
	l.AgreementDate,
	l.ClosingDate,
	l.MaturityDateCurrent,'{insertdate}' as InsertDAte,

	l.Status,l.[loLoanID] as LOLOANID
FROM [solidis].dbo.[Solidis_initial_loan] il
JOIN CBS.dbo.loLoan l  ON l.loLoanID  = il.[LOLOANID] 
join CBS.dbo.loLoanBalanceOnDate lb on lb.loLoanID=l.loLoanID
left join [solidis].dbo.[Solidis_loan_closed] ilc on ilc.[ID CREDIT] =il.[ID CREDIT]

where '{d}' between lb.[Date] and  ISNULL(lb.DateValidTo,'{d}')


and ilc.[ID CREDIT] is null


""".format(d=date_str,insertdate=insertDate_str)
print(sql)
df_update=pd.read_sql(sql,con)


df_update=df_update[['ID CREDIT','LOLOANID','N° CIN','Encours','DaysInArrears','InsertDAte']]
fn=generate_filename("PAMF_DIG EMG ",dt,"")

df_update=upload_df_to_sftp(df_update, remote_path='/pamf-to-solidis/GUICHET_CREDITS_DIGITAUX/ENCOURS/', filename=fn)
print(fn)

engine = getEngine()
df_update.to_sql(name='Solidis_loan_update',
                        con=engine,
                        if_exists='append',
                        index=False)
df_closed=df_update[df_update['Encours']==0]

df_closed=df_closed[['ID CREDIT','N° CIN','Encours','DaysInArrears','InsertDAte']]
df_closed.to_sql(name='Solidis_loan_closed',
                        con=engine,
                        if_exists='append',
                        index=False)


df_ok.to_excel('df_ok.xlsx')
df_ko.to_excel('df_ko.xlsx')
'''
