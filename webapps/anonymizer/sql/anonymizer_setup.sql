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

-- Create a function that return random code value from codes
Create or replace function random_code_value(koodiston_nimi CHAR, exclude_codes CHAR[] default '{}')
    RETURNS CHAR AS
$$
BEGIN
    RETURN (select code_value from varda_z2_code c join varda_z2_koodisto k on k.id=c.koodisto_id where k.name=koodiston_nimi and not c.code_value = any(exclude_codes) order by random() limit 1);
END;
$$ language plpgsql;


-- Create a function that returns unique tutkinto code for henkilo-vakajarjestaja pair
Create or replace function unique_tutkinto_code(_henkilo_id INT, _vakajarjestaja_id INT, _tutkinto_koodi CHAR)
    RETURNS CHAR AS
$$
DECLARE
    existing_codes VARCHAR[];
    code_value VARCHAR;
BEGIN
    existing_codes := (select ARRAY(select tutkinto_koodi from varda_tutkinto where henkilo_id=_henkilo_id and vakajarjestaja_id=_vakajarjestaja_id));
    code_value := random_code_value('tutkinto_koodit', existing_codes);
    if code_value is null then
        -- Leave as is because no suitable code was found
        return _tutkinto_koodi;
    end if;
    return code_value;
END;
$$ language plpgsql;
