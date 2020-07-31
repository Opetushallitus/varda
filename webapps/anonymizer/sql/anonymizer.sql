-- Create function that generates random strings
Create or replace function random_string(length integer) returns text as
$$
declare
  chars text[] := '{A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,Å,Ä,Ö,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,å,ä,ö}';
  result text := '';
  i integer := 0;
begin
  if length < 0 then
    raise exception 'Given length cannot be less than 0';
  end if;
  for i in 1..length loop
    result := result || chars[1+random()*(array_length(chars, 1)-1)];
  end loop;
  return result;
end;
$$ language plpgsql;

-- Create a function that generates random int between numbers
Create or replace function random_between(low INT, high INT)
    RETURNS INT AS
$$
BEGIN
    RETURN floor(random() * (high - low + 1) + low);
END;
$$ language plpgsql;


-- NORMAL TABLES
-- Table: varda_henkilo
-- Columns: henkilo_oid, etunimet, kutsumanimi, katuosoite, postinumero, postitoimipaikka

-- henkilo_oid (generate random strings)
UPDATE varda_henkilo SET henkilo_oid = concat('1.2.246.562.24.', trunc(id + 10000000000)::text) WHERE henkilo_oid <> '';


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


-- katuosoite (generate random strings)
UPDATE varda_henkilo SET katuosoite = random_string(15) from generate_series(1,15) WHERE katuosoite <> '';
UPDATE varda_henkilo SET katuosoite = concat(katuosoite, ' ', trunc(random() * 98 + 1)::text) WHERE katuosoite <> '';


-- postinumero (generate random strings)
UPDATE varda_henkilo SET postinumero = trunc(random() * 89999 + 10000)::text WHERE postinumero <> '';


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



-- Table: varda_toimipaikka
-- Columns: nimi, nimi_sv, kayntiosoite, kayntiosoite_postinumero, kayntiosoite_postitoimipaikka, postiosoite, postinumero, postitoimipaikka, puhelinnumero, sahkopostiosoite, alkamis_pvm, paattymis_pvm

-- nimi, nimi_sv (generate random strings)
UPDATE varda_toimipaikka SET nimi = random_string(15) from generate_series(1,15) WHERE nimi <> '' and toimintamuoto_koodi <> 'tm01';
UPDATE varda_toimipaikka SET nimi_sv = random_string(15) from generate_series(1,15) WHERE nimi_sv <> '' and toimintamuoto_koodi <> 'tm01';


-- kayntiosoite (generate random strings)
UPDATE varda_toimipaikka SET kayntiosoite = random_string(15) from generate_series(1,15) WHERE kayntiosoite <> '' and toimintamuoto_koodi <> 'tm01';
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
UPDATE varda_toimipaikka SET postiosoite = random_string(15) from generate_series(1,15) WHERE postiosoite <> '' and toimintamuoto_koodi <> 'tm01';
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



-- Table: varda_varhaiskasvatuspaatos
-- Columns: hakemus_pvm, alkamis_pvm, paattymis_pvm, tuntimaara_viikossa

-- hakemus_pvm (subtract random number of days 0 - 365 from the existing date)
UPDATE varda_varhaiskasvatuspaatos SET hakemus_pvm = date(hakemus_pvm - trunc(random() * 365) * '1 day'::interval * random()) WHERE hakemus_pvm IS NOT NULL;


-- alkamis_pvm (add random number of days 0 - 365 to the existing date)
UPDATE varda_varhaiskasvatuspaatos SET alkamis_pvm = date(hakemus_pvm + trunc(random() * 365) * '1 day'::interval * random()) WHERE alkamis_pvm IS NOT NULL;


-- paattymis_pvm (add random number of days 0 - 365 to the existing date)
UPDATE varda_varhaiskasvatuspaatos SET paattymis_pvm = date(alkamis_pvm + trunc(random() * 365) * '1 day'::interval * random()) WHERE paattymis_pvm IS NOT NULL;


-- tuntimaara_viikossa (randomize number between allowed numbers)
UPDATE varda_varhaiskasvatuspaatos SET tuntimaara_viikossa = random_between(1, 120);



-- Table: varda_varhaiskasvatussuhde
-- Columns: alkamis_pvm, paattymis_pvm

-- alkamis_pvm (subtract random number of days 0 - 365 from the existing date)
UPDATE varda_varhaiskasvatussuhde SET alkamis_pvm = date(alkamis_pvm - trunc(random() * 365) * '1 day'::interval * random()) WHERE alkamis_pvm IS NOT NULL;


-- paattymis_pvm (add random number of days 0 - 365 to the existing date)
UPDATE varda_varhaiskasvatussuhde SET paattymis_pvm = date(paattymis_pvm + trunc(random() * 365) * '1 day'::interval * random()) WHERE paattymis_pvm IS NOT NULL;



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
-- Table: varda_historicalhenkilo
UPDATE varda_historicalhenkilo
SET henkilo_oid = t.henkilo_oid, etunimet = t.etunimet, kutsumanimi = t.kutsumanimi, katuosoite = t.katuosoite, postinumero = t.postinumero, postitoimipaikka = t.postitoimipaikka
FROM varda_henkilo t
WHERE varda_historicalhenkilo.id = t.id;

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


-- MISC
-- Prepare Hetu fields for anonymization
UPDATE varda_henkilo SET henkilotunnus = random_string(15) from generate_series(1,15) WHERE henkilotunnus <> '';

-- Disable all background tasks
UPDATE django_celery_beat_periodictask SET enabled = false; 

-- Clean up
DROP FUNCTION IF EXISTS random_string;
DROP FUNCTION IF EXISTS random_between;
DROP TABLE IF EXISTS tmp_org;
