Klant wil:
Je klant wil een applicatie voor restaurants om bestellingen en leveringen te beheren, inclusief integratie met externe bezorgdiensten. Vergelijkbare voorbeelden zijn Uber Eats en Deliveroo.

1) Interoperability
    De klant wil "integratie met extrene bezorgdiensten" dus dit is zeker een must. Elke dienst heeft zijn eigen API en het systeem moet nieuwe diensten kunnen toevoegen en verwerken.

2) Elasticiteit
    Afhankelijk het uur zullen er meer of minder requests zijn. Dit mag de kwaliteit van de ervaring niet omlaag halen.

3) Recoverability
    Als het systeem uitvalt tijdens een bestelling moet het terug kunnen verder werken zonder data te verliezen. Anders zouden klanten die al betaald hebben hun bestellingen niet kunnen krijgen.

4) Accuracy
    Een bestelling die betaald is moet altijd correct zijn en effectief aankomen. Als een bestelling niet aankomt is dat niet acceptabel en een groot probleem voor de klant en de firma.

5) Security
    Wanneer een klant zijn of haar bankgegevens ingeeft om een bestelling te voltooien en te betalen mag er geen mogelijkheid zijn dat die gegevens vrijkomen. Over het algemeen moeten de gegevens van de klant privé gehouden worden tenzij anders vermeld.

6) Availability
    Als een klant op de piek van de dag besteld moet de ervaring van het gebruik van de applicatie even goed zijn als wanneer er nauwelijks requests binnen komen.

7) Fault tolerance
    Wanneer er iets fout gaat moet het systeem blijven werken en dus overschakelen naar een andere optie. Als bijvoorbeeld Uber Eats niet beschikbaar is moet het systeem automatisch een andere bezorgdiesnt gebruiken
