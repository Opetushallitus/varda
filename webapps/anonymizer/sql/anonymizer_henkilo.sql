-- NORMAL TABLES
-- Table: varda_henkilo
-- Columns: henkilo_oid, etunimet, kutsumanimi, katuosoite, postinumero, postitoimipaikka

-- henkilo_oid (generate random strings)
UPDATE varda_henkilo SET henkilo_oid = concat('1.2.246.562.24.', trunc(id + 10000000000)::text) WHERE henkilo_oid <> '';

-- katuosoite & postiosoite for history tables
UPDATE varda_henkilo SET katuosoite = 'Placeholder', postinumero = '00000';

-- postitoimipaikka (shuffle not-null and non-empty values)
WITH p1 AS (
    SELECT row_number() over (order by random()) n,
           postitoimipaikka AS postitoimipaikka1
    FROM varda_henkilo WHERE postitoimipaikka <> ''
),
p2 AS (
    SELECT row_number() over (order by random()) n,
           id AS id2
    FROM varda_henkilo WHERE postitoimipaikka <> ''
)
UPDATE varda_henkilo
SET postitoimipaikka = p1.postitoimipaikka1
FROM p1 join p2 on p1.n = p2.n
WHERE id = p2.id2;
