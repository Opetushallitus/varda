-- NORMAL TABLES
-- Table: varda_toimipaikka
-- Columns: nimi, nimi_sv, kayntiosoite, kayntiosoite_postinumero, kayntiosoite_postitoimipaikka, postiosoite, postinumero, postitoimipaikka, puhelinnumero, sahkopostiosoite, alkamis_pvm, paattymis_pvm

-- nimi, nimi_sv (generate random strings)
UPDATE varda_toimipaikka SET nimi = random_string(10) from generate_series(1,10) WHERE nimi <> '' and toimintamuoto_koodi <> 'tm01';
UPDATE varda_toimipaikka SET nimi_sv = random_string(10) from generate_series(1,10) WHERE nimi_sv <> '' and toimintamuoto_koodi <> 'tm01';


-- kayntiosoite (generate random strings)
UPDATE varda_toimipaikka SET kayntiosoite = random_string(10) from generate_series(1,10) WHERE kayntiosoite <> '' and toimintamuoto_koodi <> 'tm01';
UPDATE varda_toimipaikka SET kayntiosoite = concat(kayntiosoite, ' ', trunc(random() * 98 + 1)::text) WHERE kayntiosoite <> '' and toimintamuoto_koodi <> 'tm01';


-- kayntiosoite_postinumero (generate random strings)
UPDATE varda_toimipaikka SET kayntiosoite_postinumero = trunc(random() * 89999 + 10000)::text WHERE kayntiosoite_postinumero <> '' and toimintamuoto_koodi <> 'tm01';


-- kayntiosoite_postitoimipaikka (shuffle not-null and non-empty values)

WITH p1 AS (
    SELECT row_number() over (order by random()) n,
           kayntiosoite_postitoimipaikka AS kayntiosoite_postitoimipaikka1
    FROM varda_toimipaikka WHERE kayntiosoite_postitoimipaikka <> '' and toimintamuoto_koodi <> 'tm01'
),
p2 AS (
    SELECT row_number() over (order by random()) n,
           id AS id2
    FROM varda_toimipaikka WHERE kayntiosoite_postitoimipaikka <> '' and toimintamuoto_koodi <> 'tm01'
)
UPDATE varda_toimipaikka
SET kayntiosoite_postitoimipaikka = p1.kayntiosoite_postitoimipaikka1
FROM p1 join p2 on p1.n = p2.n
WHERE id = p2.id2;


-- postiosoite (generate random strings)
UPDATE varda_toimipaikka SET postiosoite = random_string(10) from generate_series(1,10) WHERE postiosoite <> '' and toimintamuoto_koodi <> 'tm01';
UPDATE varda_toimipaikka SET postiosoite = concat(postiosoite, ' ', trunc(random() * 98 + 1)::text) WHERE postiosoite <> '' and toimintamuoto_koodi <> 'tm01';


-- postinumero (generate random strings)
UPDATE varda_toimipaikka SET postinumero = trunc(random() * 89999 + 10000)::text WHERE postinumero <> '' and toimintamuoto_koodi <> 'tm01';


-- postitoimipaikka (shuffle not-null and non-empty values)
WITH p1 AS (
    SELECT row_number() over (order by random()) n,
           postitoimipaikka AS postitoimipaikka1
    FROM varda_toimipaikka WHERE postitoimipaikka <> '' and toimintamuoto_koodi <> 'tm01'
),
p2 AS (
    SELECT row_number() over (order by random()) n,
           id AS id2
    FROM varda_toimipaikka WHERE postitoimipaikka <> '' and toimintamuoto_koodi <> 'tm01'
)
UPDATE varda_toimipaikka
SET postitoimipaikka = p1.postitoimipaikka1
FROM p1 join p2 on p1.n = p2.n
WHERE id = p2.id2;


-- puhelinnumero (generate random strings)
UPDATE varda_toimipaikka SET puhelinnumero = concat('+358', trunc(random() * 899999999 + 100000000)::text) WHERE puhelinnumero <> '';


-- sahkopostiosoite (generate random strings)
UPDATE varda_toimipaikka SET sahkopostiosoite = concat('email-', trunc(random() * 8999 + 1000)::text, '@example.com');





-- Table: varda_organisaatio
-- Columns: nimi, sahkopostiosoite, kayntiosoite, kayntiosoite_postinumero, kayntiosoite_postitoimipaikka, postiosoite, postinumero, postitoimipaikka, puhelinnumero, alkamis_pvm, paattymis_pvm

-- sahkopostiosoite (generate random strings)
UPDATE varda_organisaatio SET sahkopostiosoite = concat('email-', trunc(random() * 8999 + 1000)::text, '@example.com');


-- puhelinnumero (generate random strings)
UPDATE varda_organisaatio SET puhelinnumero = concat('+358', trunc(random() * 899999999 + 100000000)::text);



-- HISTORICAL TABLES
-- Table: varda_historicaltoimipaikka
UPDATE varda_historicaltoimipaikka
SET nimi = t.nimi, nimi_sv = t.nimi_sv, kayntiosoite = t.kayntiosoite, kayntiosoite_postinumero = t.kayntiosoite_postinumero, kayntiosoite_postitoimipaikka = t.kayntiosoite_postitoimipaikka, postiosoite = t.postiosoite, postinumero = t.postinumero, postitoimipaikka = t.postitoimipaikka, puhelinnumero = t.puhelinnumero, sahkopostiosoite = t.sahkopostiosoite
FROM varda_toimipaikka t
WHERE varda_historicaltoimipaikka.id = t.id;

-- Table: varda_historicalorganisaatio
UPDATE varda_historicalorganisaatio
SET sahkopostiosoite = t.sahkopostiosoite, puhelinnumero = t.puhelinnumero
FROM varda_organisaatio t
WHERE varda_historicalorganisaatio.id = t.id;
