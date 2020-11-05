-- NORMAL TABLES
-- Table: varda_henkilo
-- Columns: henkilo_oid, etunimet, kutsumanimi, katuosoite, postinumero, postitoimipaikka

-- henkilo_oid (generate random strings)
UPDATE varda_henkilo SET henkilo_oid = concat('1.2.246.562.24.', trunc(id + 10000000000)::text) WHERE henkilo_oid <> '';

-- katuosoite & postiosoite for history tables
UPDATE varda_henkilo SET katuosoite = 'Placeholder', postinumero = '00000';

-- etunimet, kutsumanimi (shuffle not-null values)
WITH p1 AS (
    SELECT row_number() over (order by random()) n,
           etunimet AS etunimet1, kutsumanimi AS kutsumanimi1
    FROM varda_henkilo WHERE etunimet <> ''
),
p2 AS (
    SELECT row_number() over (order by random()) n,
           id AS id2
    FROM varda_henkilo WHERE etunimet <> ''
)
UPDATE varda_henkilo
SET etunimet = p1.etunimet1, kutsumanimi = p1.kutsumanimi1
FROM p1 join p2 on p1.n = p2.n
WHERE id = p2.id2;


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



-- HISTORICAL TABLES
-- Table: varda_historicalhenkilo
UPDATE varda_historicalhenkilo
SET henkilo_oid = t.henkilo_oid, etunimet = t.etunimet, kutsumanimi = t.kutsumanimi, katuosoite = t.katuosoite, postinumero = t.postinumero, postitoimipaikka = t.postitoimipaikka
FROM varda_henkilo t
WHERE varda_historicalhenkilo.id = t.id;

-- MISC
-- Prepare Hetu fields for anonymization
UPDATE varda_henkilo SET henkilotunnus = random_string(15) from generate_series(1,15) WHERE henkilotunnus <> '';

-- Disable all background tasks
UPDATE django_celery_beat_periodictask SET enabled = false;
