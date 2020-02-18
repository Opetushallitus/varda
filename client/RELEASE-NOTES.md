# Release notes
Varda-käyttöliittymä release notes

## [1.3.5] (18.02.2020)
- CSCVARDA-1408: Lisätty tarkempi validointi varhaiskasvatussuhteen alkamis_pvm:ään.
- CSCVARDA-1368: Sivujen otsikoiden ja asetteluiden johdonmukaisuus.

## [1.3.4] (28.01.2020)
- Uusi järjestämismuoto jm05
- Vakajärjestäjän sähköpostiosoitteen validoinnin yhtenäistäminen
- Katselunäkymän lasten ja toimipaikkojen sivutus

## [1.3.3] (20.01.2020)
- Selkeytetty virheviestejä lasten tietojen lomakkeella Palveluseteli ja ostopalvelu -tapauksissa.

## [1.3.2] (03.01.2020)
- Sähköpostikentän validoinnin korjaus (nyt _ on ok)
- Suorituskykyoptimointeja

## [1.3.1] (31.12.2019)
- Näytä ID paos-hallinta -sivulla
- Bugikorjauksia

## [1.3.0] (19.12.2019)
- Yksityisten varhaiskasvatusjärjestäjien kirjautuminen
- Palveluseteli- ja ostopalvelukokonaisuus
- Bugikorjauksia

## [1.2.9] (3.12.2019)
- Salli yhden päivän maksutiedot
- Summanäkymän lapsen tietojen näyttämisen uudistus

## [1.2.8] (25.11.2019)
- Bugikorjauksia
  - Korjaa maksutietojen näyttäminen yhteenveto-näkymässä

## [1.2.7] (18.11.2019)
- Bugikorjauksia
  - Hae ja muokkaa -näyttö / "Hae lisaa" -nappi: nykyisen sivun sijainti korjattu
  - Hae ja muokkaa -näyttö: Henkilohaun maksutietojen filtterointi korjattu

## [1.2.6] (30.10.2019)
- Toimipaikan nimen validointia parannettu
  - Nyt sallitaan usaempia erikoismerkkejä

## [1.2.5] (15.10.2019)
- Katsele tietoja:
  - Yhteenvetonäkymä:
    - Aktiivinen termit vaihdettu voimassaoleva-termeihin

## [1.2.4] (11.10.2019)
- Hae ja muokkaa - hakutuloksien rajaaminen
- Koodistot järjestetty aakkosjärjestykseen kielen perusteella
- Maksutietolomake tallenna nappi aktiiviseksi kun muokattu jotain
- Lomakkeiden numerokenttien pitää hyväksyä pilkku
- Linkki saavutettavuusselosteeseen
- Bugikorjauksia
  - Varhaiskasvatussuhteen kentät muokattavassa, vaikka ei pitäisi olla
  - Katsele tietoja -näkymässä ylimääräinen riviväli
  - Tieto evästeistä tulee aina suomeksi
  - Katsele tietoja-sivun Toimipaikan nimi -haku on rikki

## [1.2.3] (30.09.2019)
- Bugikorjauksia:
  - Syötä tietoja-näkymä on ollut piilossa joissain tilanteissa aikaisemmin, vaikka virkailijan käyttöoikeudet kunnossa.
  - Toimijan vaihto ei ole aina aikaisemmin toiminut (validi jos virkailijalla oikeudet useampaan organisaatioon).
  - Aikaisemmin Syötä tietoja-sivulla oleva Lisää toimipaikka -lomake ei auennut, jos toimipaikan lisäämisen aloitti tilanteessa, jossa toimipaikka-valintalista on tyhjä.

## [1.2.2] (20.09.2019)
- Maksutiedot lisätty Tietojen katselu -näkymään

## [1.2.1] (16.09.2019)
- Bugikorjauksia
- Maksutieto luokat MP02 ja MP03:
     -Lisätty mahdollisuus lisätä maksutietoja joissa sekä asiakasmaksu että palvelusetelin arvo ovat 0

## [1.2.0] (27.08.2019)
- Maksutiedot lisätty

## [1.1.6] - 15.07.2019
- Toimipaikan OID näkyy muokkausnäkymässä
- Varhaiskasvatussuhde ei voi alkaa tai päättyä toimipaikan päättymisen jälkeen

## [1.1.5] - 01.07.2019
- Varhaiskasvatuspäätöksen tuntimäärä minimissään 1h
- validointeja päivitetty

## [1.1.4] - 12.06.2019
- Frontend-sovelluksen node ja angular versiot päivitetty
- Uusi vakajarjestajat -rajapinta otettu käyttöön
- Bugikorjauksia:
  - Käyttöliittymässä vakapaikat 0 -> näyttää viivaa
  - Tyhjä sininen laatikko vakasuhteen lisäämisessä
  - UI / Etunimistä näkyy vain ensimmäinen
  - Toimipaikan lisääminen ei toimi

## [1.1.2] - 16.05.2019
- Toimipaikkojen sorttaus aakkosittain raportoinnissa

## [1.1.1] - 15.05.2019
- Etusivun toimipaikka-alasvetovalikko järjestetty aakkosittain
- Yhteenveto lisätty käyttöliittymän ohjeisiin
- Bugikorjauksia:
  - Fonttikokoa ei voinut kasvattaa toimipaikka/lapsi-näkymissä.

## [1.1.0] - 15.04.2019
- Yhteenvetonäkymä: Summatason tietoa vakajärjestäjä-tasolla. Esim. toimipaikkojen lkm ja lasten lkm.

## [1.0.3] - 28.02.2019
- Lisäyksiä virheviesteihin
- Lukumäärät toimipaikoista ja lapsista Tietojen katselu-sivulle

## [1.0.2] - 21.02.2019
- Korjauksia sivutettuihin hakuihin

## [1.0.1] - 20.02.2019
- Korjauksia vakajärjestäjä- yms. sivutettuihin hakuihin

## [1.0.0] - 05.02.2019
- Korjauksia vuorohoitokytkimien näkyvyyksiin
- Päivitetty ohjeita
- Tuotanto-release

## [0.9.5] - 30.01.2019
- Muutoksia vakapäätös- ja vakasuhdelomakkeen kenttien muokkaukseen
- Virheviestin päivittämistä
- Vakajärjestäjien sorttaus
- Henkilölomakkeen nimivalidointeja

## [0.9.4] - 15.01.2019
- Validointeja henkilölomakkeen kenttiin
- Palvelukäyttäjän kirjautumisenesto
- Virheviestien päivitys mitätöitäessä
- Vanhentuneiden kunta- ja kielikoodien pois filtteröinti
- Henkilön syötön virheenkäsittelyä paranneltu
- Käännöksiä

## [0.9.3] - 04.01.2019
- SV-käyttöohjeet
- Korjattu henkilölistauksen päivitys mitätöitäessä

## [0.9.2] - 03.01.2019
- UI:n sv-tekstit
- Toimipaikan kenttien muokkaussääntöjä muutettu

## [0.9.1] - 28.12.2018
- Kieli- ja kuntakoodisto-integraation virheenkäsittely
- Painotusten mitätöinnin virheenkäsittely
- Toimipaikkalomakkeen pakollisuuksia päivitetty

## [0.9.0] - 20.12.2018
- Lisää lapsi / lomakemuokkaus
- Näkymät käyttöoikeuksien mukaan

## [0.8.0] - 14.12.2018
- Päivitetty suomenkieliset käyttöohjeet
