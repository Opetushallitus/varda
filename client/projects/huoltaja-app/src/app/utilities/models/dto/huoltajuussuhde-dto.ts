export interface HuoltajatiedotDTO {
  huoltaja_id: number;
  huoltajuussuhteet: Array<HuoltajuussuhdeDTO>;
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
