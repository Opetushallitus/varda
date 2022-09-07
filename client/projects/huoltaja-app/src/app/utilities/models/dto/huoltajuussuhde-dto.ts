export interface HuoltajatiedotDTO {
  huoltaja_id: number;
  huoltajuussuhteet: Array<HuoltajuussuhdeDTO>;
}

export interface HuoltajatiedotSimpleDTO extends Omit<HuoltajatiedotDTO, 'huoltajuussuhteet'> {
  huoltajuussuhteet: Array<HuoltajuussuhdeSimpleDTO>;
}

export interface MaksutietoDTO {
  id: number;
  yksityinen_jarjestaja: boolean;
  maksun_peruste_koodi: string;
  palveluseteli_arvo: string;
  asiakasmaksu: string;
  perheen_koko: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  huoltaja_lkm: number;
}

export interface HuoltajuussuhdeDTO {
  aktiivinen_toimija: boolean;
  lapsi_id: number;
  lapsi_etunimet: string;
  lapsi_kutsumanimi: string;
  lapsi_sukunimi: string;
  lapsi_henkilo_id: number;
  lapsi_henkilo_oid: string;
  vakatoimija_id: number;
  vakatoimija_oid: string;
  vakatoimija_nimi: string;
  oma_organisaatio_id?: number;
  oma_organisaatio_oid?: string;
  oma_organisaatio_nimi?: string;
  paos_organisaatio_id?: number;
  paos_organisaatio_oid?: string;
  paos_organisaatio_nimi?: string;
  voimassa_kytkin: boolean;
  maksutiedot: Array<MaksutietoDTO>;
  yhteysosoite: string;
}

export interface HuoltajuussuhdeSimpleDTO {
  aktiivinen_toimija: boolean;
  lapsi_etunimet: string;
  lapsi_sukunimi: string;
  lapsi_henkilo_id: number;
  organisaatio_id: number;
  organisaatio_nimi: string;
  maksutiedot: Array<MaksutietoDTO>;
  yhteysosoite: string;
}
