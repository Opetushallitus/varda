import { HenkiloRooliEnum } from '../enums/henkilorooli.enum';
import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export interface VardaLapsiDTO {
  url: string;
  id: number;
  henkilo: string;
  paos_kytkin: boolean;
  henkilo_oid: string;
  vakatoimija_oid: string | null;
  oma_organisaatio_oid: string | null;
  oma_organisaatio_nimi: string | null;
  paos_organisaatio_oid: string | null;
  paos_organisaatio_nimi: string | null;
  lahdejarjestelma: Lahdejarjestelma | null;
  tunniste: string | null;
  muutos_pvm: string;
}


export interface LapsiListDTO {
  id: number;
  url: string;
  henkilo_id: number;
  henkilo_oid: string;
  rooli: HenkiloRooliEnum;
  vakatoimija_oid: string;
  vakatoimija_nimi: string;
  oma_organisaatio_oid: string;
  oma_organisaatio_nimi: string;
  paos_organisaatio_oid: string;
  paos_organisaatio_nimi: string;
  tallentaja_organisaatio_oid: string;
  etunimet: string;
  sukunimi: string;
  is_missing_data?: boolean;
}

export interface VardaVarhaiskasvatuspaatosDTO {
  id: number;
  url: string;
  lapsi: string;
  vuorohoito_kytkin: boolean;
  pikakasittely_kytkin: boolean;
  tuntimaara_viikossa: number;
  paivittainen_vaka_kytkin: boolean | null;
  kokopaivainen_vaka_kytkin: boolean | null;
  tilapainen_vaka_kytkin: boolean;
  jarjestamismuoto_koodi: string;
  hakemus_pvm: string;
  alkamis_pvm: string;
  paattymis_pvm: string | null;
  lahdejarjestelma: Lahdejarjestelma | null;
  tunniste: string | null;
}

export interface VardaVarhaiskasvatussuhdeDTO {
  id: number;
  url: string;
  varhaiskasvatuspaatos: string;
  toimipaikka: string;
  toimipaikka_oid: string | null;
  alkamis_pvm: string;
  paattymis_pvm: string | null;
  lahdejarjestelma: Lahdejarjestelma | null;
  tunniste: string | null;
}

export interface VardaMaksutietoDTO {
  url: string;
  id: number;
  huoltajat: Array<HuoltajaDTO>;
  lapsi: string;
  maksun_peruste_koodi: string;
  palveluseteli_arvo: string; // float number
  asiakasmaksu: string; // float number
  perheen_koko: number;
  alkamis_pvm: string; // YYYY-MM-dd
  paattymis_pvm: string | null; // YYYY-MM-dd
  tallennetut_huoltajat_count: number;
  ei_tallennetut_huoltajat_count: number;
  lahdejarjestelma: Lahdejarjestelma | null;
  tunniste: string | null;
}

export interface VardaMaksutietoSaveDTO extends Omit<VardaMaksutietoDTO, 'huoltajat'> {
  huoltajat?: Array<HuoltajaSaveDTO>;
  huoltajat_add?: Array<HuoltajaSaveDTO>;
}

export interface HuoltajaDTO {
  henkilotunnus?: string;
  henkilo_oid: string;
  etunimet: string;
  sukunimi: string;
}

export interface HuoltajaSaveDTO {
  henkilotunnus?: string;
  henkilo_oid?: string;
  etunimet: string;
  sukunimi: string;
}
