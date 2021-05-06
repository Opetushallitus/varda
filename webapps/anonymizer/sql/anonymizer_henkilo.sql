-- NORMAL TABLES
-- Table: varda_henkilo
-- Columns: henkilo_oid, etunimet, kutsumanimi, katuosoite, postinumero, postitoimipaikka

-- varda_henkilo (to avoid duplicates in the python bulk-update)
UPDATE varda_henkilo SET henkilotunnus_unique_hash = '', henkilotunnus = '', henkilo_oid = '',
                         katuosoite = 'Placeholder', postinumero = '00000';

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
