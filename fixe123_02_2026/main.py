import pandas as pd
import os

"""
path='./input/'
#need to read and append in a dataframe all file in the file_folder, file name format PAMF_DIG F2 01022026.xlsx
#read columns name N° CIN as string to avoid losing leading zeros, and reportDate as date
def read_f2_files(file_folder):
    df_f2 = pd.DataFrame()
    df_list = []
    for file in os.listdir(file_folder):
        if file.startswith("PAMF_DIG F2") and file.endswith(".xlsx"):
            df_temp = pd.read_excel(os.path.join(file_folder, file), dtype={'N° CIN': str})
            
            df_list.append(df_temp)
    df_f2 = pd.concat(df_list, ignore_index=True)
    return df_f2

df=read_f2_files(path)
df.to_excel('./output/combined_f2.xlsx', index=False)
    
"""
df_fev_partial = pd.read_excel("./123.xlsx", dtype={"N° CIN": str})
df_fev_partial["priority"] = 1
df_fev_partial["source"] = "123.xlsx"
df_fev_full = pd.read_excel(
    "./PAMF_DIG F2 - mothly2026-02-28.xlsx", dtype={"N° CIN": str}
)
df_fev_full["priority"] = 2
df_fev_full["source"] = "PAMF_DIG F2 - mothly2026-02-28.xlsx"
df_annul = pd.read_excel("annulation_pret.xlsx")
list_AgreementNumber_annul = df_annul["AgreementNumber"].tolist()


def is_annul(agreement_number):
    if agreement_number in list_AgreementNumber_annul:
        return True
    else:
        return False


def not_in_init(agreement_number):
    if agreement_number not in list_AgreementNumber_annul:
        return True
    else:
        return False


df_fev_partial["LOLOANID"] = 0
df_fev_partial["is_annul"] = df_fev_partial["ID CREDIT"].apply(is_annul)
df_fev_full["is_annul"] = False

print(df_fev_partial.columns)

columns_finale = [
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
    "priority",
    "source",
    "LOLOANID",
    "is_annul",
]

df_fev_finale = pd.concat(
    [df_fev_partial[columns_finale], df_fev_full[columns_finale]], ignore_index=True
)

# sorting by ID CREDIT and priority to have the partial data on top of the full data for the same ID CREDIT
df_fev_finale.sort_values(by=["ID CREDIT", "priority"], inplace=True)

# adding columns 'is_duplicated' to identify duplicated ID CREDIT
df_fev_finale["is_duplicated"] = df_fev_finale.duplicated(
    subset=["ID CREDIT"], keep=False
)

# delete duplicate and keep the first priority which is the partial data
df_fev_finale.drop_duplicates(subset=["ID CREDIT"], keep="first", inplace=True)


df_fev_finale.to_excel("./output/fev_finale.xlsx", index=False)
