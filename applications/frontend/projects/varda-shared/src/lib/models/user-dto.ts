export class VardaUserDTO {
  toimintakieli_koodi?: string;
  email?: string;
  henkilo_oid?: string;
  username?: string;
  kayttooikeudet?: Array<any>;
  kayttajatyyppi?: string;
  etunimet?: string;
  kutsumanimi?: string;
  sukunimi?: string;
  huollettava_list?: Array<UserHuollettavaDTO>;
}


export class UserHuollettavaDTO {
  etunimet: string;
  henkilo_oid: string;
  kutsumanimi: string;
  sukunimi: string;
}
