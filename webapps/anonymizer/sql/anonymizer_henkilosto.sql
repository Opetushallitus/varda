--HENKILOSTO TABLES

-- Table varda_palvelussuhde
UPDATE varda_palvelussuhde SET alkamis_pvm = date(alkamis_pvm - trunc(random() * 365) * '1 day'::interval * random()),
                               tyosuhde_koodi = random_between(1, 2),
                               tyoaika_koodi = random_between(1,2),
                               tutkinto_koodi = random_code_value(11),
                               tyoaika_viikossa = random_between(1, 50),
                               tunniste = id;
UPDATE varda_palvelussuhde SET paattymis_pvm = date(paattymis_pvm + trunc(random() * 365) * '1 day'::interval * random()) Where paattymis_pvm is NOT NULL;

-- Table varda_tyoskentelypaikka
UPDATE varda_tyoskentelypaikka SET tehtavanimike_koodi = random_code_value(9),
                                   alkamis_pvm = (select CASE WHEN pal.paattymis_pvm is not NULL THEN pal.alkamis_pvm + random() * '1 day'::interval * (pal.paattymis_pvm - pal.alkamis_pvm)
                                                              ELSE date(pal.alkamis_pvm + trunc(random() * 365) * '1 day'::interval * random())
                                                              END AS alkamis_pvm
                                                     from varda_palvelussuhde pal
                                                     where pal.id = varda_tyoskentelypaikka.palvelussuhde_id),
                                   tunniste = id;

UPDATE varda_tyoskentelypaikka SET paattymis_pvm = (SELECT CASE WHEN pal.paattymis_pvm is not NULL THEN varda_tyoskentelypaikka.alkamis_pvm + (random() * '1 day'::interval * (pal.paattymis_pvm - varda_tyoskentelypaikka.alkamis_pvm))
                                                                ELSE NULL
                                                                END AS paattymis_pvm
                                                       FROM varda_palvelussuhde pal
                                                       WHERE pal.id = varda_tyoskentelypaikka.palvelussuhde_id)
                               WHERE paattymis_pvm is NOT NULL;

-- Table varda_pidempipoissaolo
UPDATE varda_pidempipoissaolo SET alkamis_pvm = (select CASE WHEN pal.paattymis_pvm is not NULL THEN pal.alkamis_pvm + random() * '1 day'::interval * (pal.paattymis_pvm - pal.alkamis_pvm)
                                                             ELSE date(pal.alkamis_pvm + trunc(random() * 365) * '1 day'::interval * random())
                                                             END AS alkamis_pvm
                                                     from varda_palvelussuhde pal
                                                     where pal.id = varda_pidempipoissaolo.palvelussuhde_id),
                                  paattymis_pvm = (SELECT CASE WHEN pal.paattymis_pvm is not NULL THEN varda_pidempipoissaolo.alkamis_pvm + (random() * '1 day'::interval * (pal.paattymis_pvm - varda_pidempipoissaolo.alkamis_pvm + 60))
                                                               ELSE NULL
                                                               END AS paattymis_pvm
                                                       FROM varda_palvelussuhde pal
                                                       WHERE pal.id = varda_pidempipoissaolo.palvelussuhde_id),
                                  tunniste = id;

-- Table varda_taydennyskoulutus
UPDATE varda_taydennyskoulutus set nimi = concat('Taydennyskoulutus ', random_between(1, 10000)),
                                   suoritus_pvm = date(suoritus_pvm + trunc(random() * 365) * '1 day'::interval * random()),
                                   tunniste = id;

-- Table varda_taydennyskoulutustyontekija
UPDATE varda_taydennyskoulutustyontekija SET tehtavanimike_koodi = random_code_value(9);

-- Table varda_tyontekija
UPDATE varda_tyontekija SET tunniste = id;

-- Table varda_tutkinto
UPDATE varda_tutkinto SET tutkinto_koodi = random_code_value(11);

-- Table varda_tilapainenhenkilosto
UPDATE varda_tilapainenhenkilosto SET tuntimaara=random(),
                                      tyontekijamaara=random_between(1, 200),
                                      tunniste = id;


-- HISTORICAL TABLES

-- HENKILOSTO history
--historical_tilapainenhenkilosto
UPDATE varda_historicaltilapainenhenkilosto
SET tuntimaara = t.tuntimaara, tyontekijamaara = t.tyontekijamaara
FROM varda_tilapainenhenkilosto t
WHERE varda_historicaltilapainenhenkilosto.id = t.id ;

--varda_historicaltyoskentelypaikka
UPDATE varda_historicaltyoskentelypaikka
SET tehtavanimike_koodi = t.tehtavanimike_koodi, alkamis_pvm = t.alkamis_pvm, paattymis_pvm = t.paattymis_pvm, tunniste = t.tunniste
FROM varda_tyoskentelypaikka t
WHERE varda_historicaltyoskentelypaikka.id = t.id;

--varda_historicalpidempipoissaolo
UPDATE varda_historicalpidempipoissaolo
SET alkamis_pvm = t.alkamis_pvm, paattymis_pvm = t.paattymis_pvm, tunniste = t.tunniste
FROM varda_pidempipoissaolo t
WHERE varda_historicalpidempipoissaolo.id = t.id;

--varda_historicalpalvelussuhde
UPDATE varda_historicalpalvelussuhde
SET alkamis_pvm = t.alkamis_pvm,
    tyosuhde_koodi = t.tyosuhde_koodi,
    tyoaika_koodi = t.tyoaika_koodi,
    tutkinto_koodi = t.tutkinto_koodi,
    tyoaika_viikossa = t.tyoaika_viikossa,
    paattymis_pvm = t.paattymis_pvm,
    tunniste = t.tunniste
FROM varda_palvelussuhde t
WHERE varda_historicalpalvelussuhde.id = t.id;

--varda_historicaltyontekija
UPDATE varda_historicaltyontekija
SET tunniste = t.tunniste
FROM varda_tyontekija t
WHERE varda_historicaltyontekija.id = t.id;

--varda_historicaltutkinto
UPDATE varda_historicaltutkinto
SET tutkinto_koodi = t.tutkinto_koodi
FROM varda_tutkinto t
WHERE varda_historicaltutkinto.id = t.id;

--varda_historicaltaydennyskoulutus
UPDATE varda_historicaltaydennyskoulutus
SET nimi = t.nimi, suoritus_pvm = t.suoritus_pvm, tunniste = t.tunniste
    FROM varda_taydennyskoulutus t
    WHERE varda_historicaltaydennyskoulutus.id = t.id;

--varda_historicaltaydennyskoulutustyontekija
UPDATE varda_historicaltaydennyskoulutustyontekija
SET tehtavanimike_koodi = t.tehtavanimike_koodi
FROM varda_taydennyskoulutustyontekija t
WHERE varda_historicaltaydennyskoulutustyontekija.id = t.id;
