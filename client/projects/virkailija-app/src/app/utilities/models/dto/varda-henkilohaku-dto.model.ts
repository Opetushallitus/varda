import {VardaHenkiloDTO} from './varda-henkilo-dto.model';

export class HenkilohakuResultDTO {
  id: number;
  url: string;
  henkilo: VardaHenkiloDTO;
  maksutiedot: Array<string>;
  toimipaikat: Array<{nimi: string, nimi_sv: string, organisaatio_oid: string, }>;
}

export enum HenkilohakuType {
  lapset = 'lapset',
  tyontekija = 'tyontekijat',
}

export enum FilterStatus {
  kaikki = 'kaikki',
  voimassaOlevat = 'voimassaolevat',
  paattyneet = 'paattyneet',
  eiMaksutietoja = 'eimaksutietoja'
}

export enum FilterObject {
  vakapaatokset = 'vakapaatokset',
  vakasuhteet = 'vakasuhteet',
  maksutiedot = 'maksutiedot'
}

export class HenkilohakuSearchDTO {
  search: string;
  type: HenkilohakuType;
  filter_status: FilterStatus;
  filter_object: FilterObject;
  page?: number;
}

export class LapsiByToimipaikkaDTO {
  etunimet: string;
  sukunimi: string;
  syntyma_pvm: string;
  henkilo_oid: string;
  oma_organisaatio_nimi: string;
  paos_organisaatio_nimi: string;
  lapsi_id: number;
  lapsi_url: string;
}

export class ToimipaikanLapsi {
  henkilo: ToimipaikanLapsiHenkilo;
  varhaiskasvatuspaatokset: Array<ToimipaikanLapsiVakapaatos>;
  varhaiskasvatussuhteet: Array<ToimipaikanLapsiVakasuhde>;
  maksutiedot: Array<ToimipaikanLapsiMaksutieto>;
  lapsi_id: number;
  oma_organisaatio_nimi: string;
  paos_organisaatio_nimi: string;
}

export class ToimipaikanLapsiHenkilo {
  etunimet: string;
  kutsumanimi: string;
  sukunimi: string;
  id: number;
  henkilo_oid: string;
  syntyma_pvm: string;
}

export class ToimipaikanLapsiHuoltaja {
  henkilo_oid: string;
  etunimet: string;
  sukunimi: string;
}

export class ToimipaikanLapsiMaksutieto {
  maksun_peruste_koodi: string;
  palveluseteli_arvo: number;
  asiakasmaksu: number;
  perheen_koko: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  huoltajat: Array<ToimipaikanLapsiHuoltaja>;
}

export class ToimipaikanLapsiVakapaatos {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  hakemus_pvm: string;
  tuntimaara_viikossa: number;
  jarjestamismuoto_koodi: string;
  paivittainen_vaka_kytkin: boolean;
  kokopaivainen_vaka_kytkin: boolean;
  vuorohoito_kytkin: boolean;
  pikakasittely_kytkin: boolean;
}

export class ToimipaikanLapsiVakasuhde {
  alkamis_pvm: string;
  paattymis_pvm: string;
  toimipaikka_nimi: string;
  varhaiskasvatuspaatos: string;
}
