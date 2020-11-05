-- NORMAL TABLES
-- Table: varda_varhaiskasvatuspaatos
-- Columns: hakemus_pvm, alkamis_pvm, paattymis_pvm, tuntimaara_viikossa

-- hakemus_pvm (subtract random number of days 0 - 365 from the existing date)
UPDATE varda_varhaiskasvatuspaatos SET hakemus_pvm = date(hakemus_pvm - trunc(random() * 365) * '1 day'::interval * random()) WHERE hakemus_pvm IS NOT NULL;


-- alkamis_pvm (subtract random number of days 0 - 365 to the existing date)
UPDATE varda_varhaiskasvatuspaatos SET alkamis_pvm = date(hakemus_pvm - trunc(random() * 365) * '1 day'::interval * random()) WHERE alkamis_pvm IS NOT NULL;


-- paattymis_pvm (add random number of days 0 - 365 to the existing date)
UPDATE varda_varhaiskasvatuspaatos SET paattymis_pvm = date(alkamis_pvm + trunc(random() * 365) * '1 day'::interval * random()) WHERE paattymis_pvm IS NOT NULL;


-- tuntimaara_viikossa (randomize number between allowed numbers)
UPDATE varda_varhaiskasvatuspaatos SET tuntimaara_viikossa = random_between(1, 120);



-- Table: varda_varhaiskasvatussuhde
-- Columns: alkamis_pvm, paattymis_pvm

-- alkamis_pvm (subtract random number of days 0 - 365 from the existing date)
UPDATE varda_varhaiskasvatussuhde SET alkamis_pvm = (select CASE WHEN vap.paattymis_pvm is not NULL THEN vap.alkamis_pvm + random() * '1 day'::interval * (vap.paattymis_pvm - vap.alkamis_pvm)
                                                                 ELSE date(vap.alkamis_pvm + trunc(random() * 365) * '1 day'::interval * random())
                                                            END AS alkamis_pvm
                                                     from varda_varhaiskasvatuspaatos vap
                                                     where vap.id = varda_varhaiskasvatussuhde.varhaiskasvatuspaatos_id);

-- paattymis_pvm (add random number of days 0 - 365 to the existing date)
UPDATE varda_varhaiskasvatussuhde SET paattymis_pvm = (SELECT CASE WHEN vap.paattymis_pvm is not NULL THEN varda_varhaiskasvatussuhde.alkamis_pvm + (random() * '1 day'::interval * (vap.paattymis_pvm - varda_varhaiskasvatussuhde.alkamis_pvm))
                                                              ELSE NULL
                                                              END AS paattymis_pvm
                                                       FROM varda_varhaiskasvatuspaatos vap
                                                       WHERE vap.id = varda_varhaiskasvatussuhde.varhaiskasvatuspaatos_id)
                                  WHERE paattymis_pvm IS NOT NULL;


--Table: varda_maksutieto
-- alkamis_pvm (subtract random number of days 0 - 365 from the existing date)
UPDATE varda_maksutieto SET alkamis_pvm = date(alkamis_pvm - trunc(random() * 365) * '1 day'::interval * random()) WHERE alkamis_pvm IS NOT NULL;


-- paattymis_pvm (add random number of days 0 - 365 to the existing date)
UPDATE varda_maksutieto SET paattymis_pvm = date(paattymis_pvm + trunc(random() * 365) * '1 day'::interval * random()) WHERE paattymis_pvm IS NOT NULL;


-- asiakasmaksu
UPDATE varda_maksutieto SET asiakasmaksu = random_between(1, 999) WHERE asiakasmaksu != 0;

-- palveluseteli_arvo
UPDATE varda_maksutieto SET palveluseteli_arvo = random_between(1, 999) WHERE palveluseteli_arvo != 0;

-- HISTORICAL TABLES

-- VARHAISKASVATUS HISTORY
-- Table: varda_historicalvarhaiskasvatuspaatos
UPDATE varda_historicalvarhaiskasvatuspaatos
SET hakemus_pvm = t.hakemus_pvm, alkamis_pvm = t.alkamis_pvm, paattymis_pvm = t.paattymis_pvm
FROM varda_varhaiskasvatuspaatos t
WHERE varda_historicalvarhaiskasvatuspaatos.id = t.id;

-- Table: varda_historicalvarhaiskasvatussuhde
UPDATE varda_historicalvarhaiskasvatussuhde
SET alkamis_pvm = t.alkamis_pvm, paattymis_pvm = t.paattymis_pvm
FROM varda_varhaiskasvatussuhde t
WHERE varda_historicalvarhaiskasvatussuhde.id = t.id;

-- Table: varda_historicalmaksutieto
UPDATE varda_historicalmaksutieto
SET alkamis_pvm = t.alkamis_pvm, paattymis_pvm = t.paattymis_pvm
FROM varda_maksutieto t
WHERE varda_historicalmaksutieto.id = t.id;
