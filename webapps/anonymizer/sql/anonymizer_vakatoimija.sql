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


-- alkamis_pvm (subtract random number of days 0 - 365 from the existing date)
UPDATE varda_toimipaikka SET alkamis_pvm = date(alkamis_pvm - trunc(random() * 365) * '1 day'::interval * random()) WHERE alkamis_pvm IS NOT NULL and toimintamuoto_koodi <> 'tm01';


-- paattymis_pvm (add random number of days 0 - 365 to the existing date)
UPDATE varda_toimipaikka SET paattymis_pvm = date(paattymis_pvm + trunc(random() * 365) * '1 day'::interval * random()) WHERE paattymis_pvm IS NOT NULL and toimintamuoto_koodi <> 'tm01';






-- Table: varda_vakajarjestaja
-- Columns: nimi, sahkopostiosoite, tilinumero, kayntiosoite, kayntiosoite_postinumero, kayntiosoite_postitoimipaikka, postiosoite, postinumero, postitoimipaikka, puhelinnumero, alkamis_pvm, paattymis_pvm

-- sahkopostiosoite (generate random strings)
UPDATE varda_vakajarjestaja SET sahkopostiosoite = concat('email-', trunc(random() * 8999 + 1000)::text, '@example.com');


-- tilinumero (generate random strings)
UPDATE varda_vakajarjestaja SET tilinumero = concat('FI', trunc(random() * 89 + 10)::text, ' ', trunc(random() * 8999 + 1000)::text, ' ', trunc(random() * 8999 + 1000)::text, ' ', trunc(random() * 8999 + 1000)::text, ' ', trunc(random() * 89 + 10)::text);


-- puhelinnumero (generate random strings)
UPDATE varda_vakajarjestaja SET puhelinnumero = concat('+358', trunc(random() * 899999999 + 100000000)::text);



-- HISTORICAL TABLES
-- Table: varda_historicaltoimipaikka
UPDATE varda_historicaltoimipaikka
SET nimi = t.nimi, nimi_sv = t.nimi_sv, kayntiosoite = t.kayntiosoite, kayntiosoite_postinumero = t.kayntiosoite_postinumero, kayntiosoite_postitoimipaikka = t.kayntiosoite_postitoimipaikka, postiosoite = t.postiosoite, postinumero = t.postinumero, postitoimipaikka = t.postitoimipaikka, puhelinnumero = t.puhelinnumero, sahkopostiosoite = t.sahkopostiosoite
FROM varda_toimipaikka t
WHERE varda_historicaltoimipaikka.id = t.id;

-- Table: varda_historicalvakajarjestaja
UPDATE varda_historicalvakajarjestaja
SET sahkopostiosoite = t.sahkopostiosoite, tilinumero = t.tilinumero, puhelinnumero = t.puhelinnumero
FROM varda_vakajarjestaja t
WHERE varda_historicalvakajarjestaja.id = t.id;