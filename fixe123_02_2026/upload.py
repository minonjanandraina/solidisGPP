import pandas as pd
import os
from sqlalchemy import create_engine, text
import platform
import urllib.parse


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


engine = getEngine()
f2 = pd.read_excel(
    "./output/PAMF_DIG F2 - mothly2026-02-28_rectif_to_send.xlsx", dtype={"N° CIN": str}
)
f2["DATOUV"] = pd.to_datetime(f2["DATOUV"])
f2["DATECH"] = pd.to_datetime(f2["DATECH"]).dt.strftime("%Y-%m-%d")
f2.to_sql(name="Solidis_initial_loan", con=engine, if_exists="append", index=False)

"""
error:
   f2.to_sql(name='Solidis_initial_loan',
  File "E:\minonja\trav\2- After20112025\solidis\script\venv\Lib\site-packages\pandas\core\generic.py", line 3052, in to_sql
    return sql.to_sql(
           ^^^^^^^^^^^
  File "E:\minonja\trav\2- After20112025\solidis\script\venv\Lib\site-packages\pandas\io\sql.py", line 841, in to_sql
    return pandas_sql.to_sql(
           ^^^^^^^^^^^^^^^^^^
  File "E:\minonja\trav\2- After20112025\solidis\script\venv\Lib\site-packages\pandas\io\sql.py", line 2037, in to_sql
    total_inserted = sql_engine.insert_records(
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\minonja\trav\2- After20112025\solidis\script\venv\Lib\site-packages\pandas\io\sql.py", line 1571, in insert_records
    return table.insert(chunksize=chunksize, method=method)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\minonja\trav\2- After20112025\solidis\script\venv\Lib\site-packages\pandas\io\sql.py", line 1122, in insert
    num_inserted = exec_insert(conn, keys, chunk_iter)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\minonja\trav\2- After20112025\solidis\script\venv\Lib\site-packages\pandas\io\sql.py", line 1014, in _execute_insert
    result = self.pd_sql.execute(self.table.insert(), data)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\minonja\trav\2- After20112025\solidis\script\venv\Lib\site-packages\pandas\io\sql.py", line 1681, in execute
    raise DatabaseError(f"Execution failed on sql '{sql}': {exc}") from exc
pandas.errors.DatabaseError: Execution failed on sql 'INSERT INTO "Solidis_initial_loan" ("LOLOANID", "REF", "ID CREDIT", "N° CIN", "DATE DE NAISSANCE", "GENRE", "AGENCE D'OCTROI", "OBJET", "CLASST", "MONTANT", "DATOUV", "DATECH", "CYCLE", "TAUX") VALUES (:LOLOANID, :REF, :ID_CREDIT, :N°_CIN, :DATE_DE_NAISSANCE, :GENRE, :AGENCE_D'OCTROI, :OBJET, :CLASST, :MONTANT, :DATOUV, :DATECH, :CYCLE, :TAUX)': (pyodbc.DataError) ('22007', "[22007] [Microsoft][ODBC SQL Server Driver][SQL Server]La conversion d'un type de données nvarchar en type de données datetime a créé une valeur hors limites. (242) (SQLExecDirectW); [22007] [Microsoft][ODBC SQL Server Driver][SQL Server]L'instruction a été arrêtée. (3621)")
[SQL: INSERT INTO [Solidis_initial_loan] ([LOLOANID], [REF], [ID CREDIT], [N° CIN], [DATE DE NAISSANCE], [GENRE], [AGENCE D'OCTROI], [OBJET], [CLASST], [MONTANT], [DATOUV], [DATECH], [CYCLE], [TAUX]) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ? ... 6405 characters truncated ...  ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: (22298950, '01152001-07-1065826-00024/22298950', '01152001-07-1065826-00024', '101222139045', '2002-04-12', 'Female', 'Digital', 'Urgence', 'H4', 268000, '2026-02-12', datetime.datetime(2026, 3, 14, 0, 0), 111, 0.09, 22299033, '01152001-07-0948501-00013/22299033', '01152001-07-0948501-00013', '711992033655', '1986-02-05', 'Female', 'Digital', 'Urgence', 'H4', 228000, '2026-02-12', datetime.datetime(2026, 3, 14, 0, 0), 27, 0.09, 22299046, '01152001-07-0965589-00025/22299046', '01152001-07-0965589-00025', '102012020349', '1997-11-10', 'Female', 'Digital', 'Urgence', 'Low', 411000, '2026-02-12', datetime.datetime(2026, 3, 14, 0, 0), 116, 0.09, 22299100, '01152001-07-0879302-00033/22299100', '01152001-07-0879302-00033', '101211256528', '2001-10-14', 'Male', 'Digital', 'Urgence' ... 1986 parameters truncated ... 'Digital', 'Urgence', 'M0', 320000, '2026-02-13', datetime.datetime(2026, 3, 15, 0, 0), 85, 0.09, 22313209, '01152001-07-1190002-00013/22313209', '01152001-07-1190002-00013', '101232121459', '1982-03-02', 'Female', 'Digital', 'Investissement agricole', 'M2', 214000, '2026-02-13', datetime.datetime(2026, 3, 15, 0, 0), 55, 0.09, 22313218, '01152001-07-1171651-00014/22313218', '01152001-07-1171651-00014', '515011007240', '1950-06-28', 'Male', 'Digital', 'Urgence', 'M2', 209000, '2026-02-13', datetime.datetime(2026, 3, 15, 0, 0), 65, 0.09, 22313275, '01152001-07-1165090-00014/22313275', '01152001-07-1165090-00014', '504092006620', '1997-01-01', 'Female', 'Digital', 'Investissement agricole', 'M1', 237000, '2026-02-13', datetime.datetime(2026, 3, 15, 0, 0), 62, 0.09)]


destination table:
CREATE TABLE [dbo].[Solidis_initial_loan](
	[LOLOANID] [float] NULL,
	[REF] [varchar](max) NULL,
	[ID CREDIT] [varchar](max) NULL,
	[N° CIN] [bigint] NULL,
	[DATE DE NAISSANCE] [varchar](max) NULL,
	[GENRE] [varchar](max) NULL,
	[AGENCE D'OCTROI] [varchar](max) NULL,
	[OBJET] [varchar](max) NULL,
	[CLASST] [varchar](max) NULL,
	[MONTANT] [bigint] NULL,
	[DATOUV] [datetime] NULL,
	[DATECH] [varchar](max) NULL,
	[CYCLE] [bigint] NULL,
	[TAUX] [float] NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
"""
