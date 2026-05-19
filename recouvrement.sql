---prompt start
PAMF: institution financier 
SOlidis: assurance de crédit
principes globale:
1- à l'entré en portfeuille, la PAMF paie à solidis 1.5% du prêt
2- à chaque 30 jours d'arriérés, la PAMF paie à solidis 1.5% du prêt restant dû
3- à chaque 61 jours d'arriérés, la solidis doit reverser 50% du prêt impayé 
4- après 61 jours de retards, tous paiement recus sur le prêt seront partagés à 50% entre la PAMF et solidis
5- ci-après les scripts sql pour extraire les recouvrements à partager à 50% entre la PAMF et solidis après 61 jours de retards


---prompt end
    SELECT 
lA.loloanAllocationID,l.AgreementDate,l.AgreementNumber,max(l.LoanAmountCurrent) as LoanAmount,max(r.Encours) as EncoursAuMomentDeLAppel,sum(case when lD.DebitType=2 then lA.AmountCRY else 0 end) totalRemboursementPrincipale,sum(case when lD.DebitType=2 then lA.AmountCRY else 0 end)/2 as recouvrementAReverser
     
    FROM [solidis].[dbo].[Solidis_loan_update_monthly_reports] r
    join cbs.dbo.loLoan l on l.loLoanID  = r.loLoanID
    join CBS.dbo.loloancredit lc on lc.loLoanId= l.loLoanID
    left join CBS.dbo.loloanAllocation lA on lA.loLoanCreditID=lc.loLoanCreditID
    left join CBS.dbo.loloanDebit lD on lD.loLoanDebitID=lA.loLoanDebitID
    where  r.DaysInArrears=61 and lA.Date>r.reportDate
    and lD.DebitType=2 
    and where lA.loloanAllocationID>'' -- ICI à remplacer par last dans la table 
	group by l.AgreementDate,l.AgreementNumber

	order by l.AgreementDate

sur la base de ce script, merci de creer un process main et un modèle pour stocker les données depuis le script SQL dans une table de base de données.

modèle 1 - RecouveryProcess: Processus principal pour extraire et stocker les données de recouvrement entre 2 date( meme principe que le module commission)
modèle 2 - RecouvrementTransaction: Table de base de données pour stocker les données de recouvrement + foreign key pour lier à la RecouveryProcess