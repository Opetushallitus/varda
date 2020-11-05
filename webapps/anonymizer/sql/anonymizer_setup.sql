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
Create or replace function random_code_value(koodiston_id INT)
    RETURNS CHAR AS
$$
BEGIN
    RETURN (select code_value from varda_z2_code z2 where z2.koodisto_id=koodiston_id order by random() limit 1);
END;
$$ language plpgsql;
