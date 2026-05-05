[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/4ki28fry)
# Domaći Zadatak 5: Implementacija CI/CD tokova za Payment servis

## Kontekst
Tokom prethodnih časova uspešno smo realizovali i demonstrirali implementaciju procesa kontinuirane integracije i isporuke (CI/CD) na primeru `inventory` servisa. Cilj ovog zadatka je samostalna primena usvojenih koncepata na aplikaciji za plaćanje (`payment`).

## Specifikacija zadatka

Vaš zadatak je da dizajnirate i implementirate automatizovane tokove (pipelines) koristeći GitHub Actions, sa ciljem osiguravanja kvaliteta koda i automatizovane isporuke kontejnerizovane aplikacije.

### 1. Upravljanje granama (Git Workflow)
*   **Preduslov:** Kreirajte novu radnu granu pod nazivom `develop` na osnovu trenutne `main` grane. Svoj kod razvijajte i inicijalno postavljajte (push) na ovu granu.
*   Spajanje (merge) u `main` granu se vrši tek kada su svi testovi na `develop` grani uspešni.
*   `develop` i `main` moraju biti zaštićene grane.

### 2. Kontinuirana integracija (Continuous Integration - CI)
Potrebno je kreirati CI pipeline koji će se automatski pokretati pri svakom push-u na bilo koju granu u repozitorijumu. Tok mora da obuhvati pokretanje definisanih testova za `payment` servis u izolovanom okruženju.
Pipeline je uspešan isključivo ukoliko uspešno prođu sledeće kategorije testova:
*   **Unit testovi:** Testiranje poslovne logike u potpunoj izolaciji, uz obavezno mokovanje (mocking) spoljnih zavisnosti.
*   **Integracioni testovi:** Testiranje interakcije između komponenti koda i infrastrukturnih servisa (npr. baze podataka, posrednika za poruke).
*   **Funkcionalni testovi:** API provere i simulacija protoka podataka posmatrajući `payment` servis kao celinu.

### 3. Kontinuirana isporuka (Continuous Deployment/Delivery - CD)
Nakon uspešne integracije, potrebno je automatizovati proces izgradnje (build) i distribucije (push) Docker slike na vaš lični DockerHub repozitorijum.
CD pipeline mora biti konfigurisan tako da se aktivira u sledećim scenarijima:
*   Prilikom svakog postavljanja koda (push) na `develop` granu.
*   Prilikom spajanja koda (merge) u `main` granu.

*Napomena: CD pipeline mora zavisiti od uspešnosti CI pipeline-a (Docker slika se ne sme build-ovati ukoliko testovi padaju).*

### 4. Konfiguracija i bezbednost kredencijala
Apsolutno je zabranjeno čuvanje (hardkodovanje) kredencijala u okviru YAML definicija tokova ili u samom kodu. 
*   Kreirajte *Personal Access Token* (PAT) na vašem DockerHub nalogu.
*   Kredencijale unosite u pipeline isključivo putem repozitorijumskih tajni (GitHub Secrets). Očekivana imena tajni koja morate postaviti u repozitorijumu su `DOCKERHUB_USERNAME` i `DOCKERHUB_TOKEN`.

### Bitne napomene:
* Rok za izradu domaćeg zadatka je **23. maj 2026**.
* Ukoliko se potencijalno jave problemi sa Konfiguracijom i bezbednošću imate pravo da uradite fork repozitorijuma u okviru ličnog GitHub naloga i da zadatak uradite kroz taj repozitrorijum. Dodatno, potrebno je na repozitorijumu domaćeg zadatka u README fajlu u okviru develop grane ostaviti link do fork-ovanog repozitorijuma ukoliko se odlučite za ovakav vid izrade.
