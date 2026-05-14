# Vereisten voor de restaurant- en bezorgapplicatie

De klant wil een applicatie voor restaurants om bestellingen en leveringen te beheren, inclusief integratie met externe bezorgdiensten. Vergelijkbare voorbeelden zijn Uber Eats en Deliveroo.

## 1. Interoperability

De klant wil integratie met externe bezorgdiensten, dus dit is een essentiële vereiste. Elke bezorgdienst heeft zijn eigen API en het systeem moet eenvoudig nieuwe diensten kunnen toevoegen en verwerken.

## 2. Elasticiteit

Afhankelijk van het tijdstip van de dag zullen er meer of minder requests zijn. Dit mag de kwaliteit van de gebruikerservaring niet negatief beïnvloeden.

## 3. Recoverability

Als het systeem uitvalt tijdens een bestelling, moet het correct kunnen herstellen zonder data te verliezen. Klanten die al betaald hebben, moeten hun bestelling nog steeds correct kunnen ontvangen.

## 4. Accuracy

Een bestelling die betaald is, moet altijd correct verwerkt en geleverd worden. Een bestelling die niet aankomt is onacceptabel en vormt een groot probleem voor zowel de klant als het bedrijf.

## 5. Security

Wanneer een klant bankgegevens invoert om een bestelling te betalen, mogen deze gegevens nooit uitlekken. In het algemeen moeten alle klantgegevens privé en beveiligd blijven, tenzij de klant expliciet anders toestemt.

## 6. Availability

Tijdens piekuren moet de applicatie even vlot blijven werken als tijdens rustige momenten. De prestaties en gebruikerservaring mogen niet verminderen bij hoge belasting.

## 7. Fault Tolerance

Wanneer er iets fout gaat, moet het systeem blijven functioneren door automatisch over te schakelen naar een alternatief. Als bijvoorbeeld Uber Eats niet beschikbaar is, moet het systeem automatisch een andere bezorgdienst kunnen gebruiken.