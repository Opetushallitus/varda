export class HuoltajaFrontpageDto {
  lapsi: LapsiDTO;
  voimassa_useita_vakapaatoksia: boolean;
  toimipaikat?: Array<ToimipaikkaDTO>;
}

export class LapsiDTO {
  henkilo_oid: string;
  henkilotunnus: string;
  etunimet: string;
  kutsumanimi: string;
  sukunimi: string;
  aidinkieli: string;
  syntymaaika: string; // YYYY-MM-dd
  sukupuoli: string;
  kotikunta: string;
  postinumero: string;
  postitoimipaikka: string;
  toggle_expanded = false;
}

export class ToimipaikkaDTO {
  nimi: string;
  vakasuhteet: Array<VarhaiskasvatussuhdeDTO>;
}

export class VarhaiskasvatussuhdeDTO {
  vakapaatos_voimassa: boolean;
  alkamis_pvm: string; // YYYY-MM-dd
  paattymis_pvm?: string; // YYYY-MM-dd
  vakapaatokset: Array<VarhaiskasvatuspaatosDTO>;
}

export class VarhaiskasvatuspaatosDTO {
  alkamis_pvm: string; // YYYY-MM-dd
  paattymis_pvm?: string; // YYYY-MM-dd
  hakemus_pvm: string; // YYYY-MM-dd
  toimipaikkaan_sijoittuminen: string;
  tuntimaara_viikossa: number;
  jarjestamismuoto: string;
  paivittainen_vaka_kytkin: boolean;
  kokopaivainen_vaka_kytkin: boolean;
  vuorohoito_kytkin?: boolean;
  osaviikkoinen_vaka_kytkin: boolean;
  osapaivainen_vaka_kytkin: boolean;
  toggle_expanded = false;
}
