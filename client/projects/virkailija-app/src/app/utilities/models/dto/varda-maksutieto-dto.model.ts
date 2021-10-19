import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaMaksutietoDTO {
  url: string;
  id: number;
  huoltajat?: Array<HuoltajaDTO>;
  huoltajat_add?: Array<HuoltajaDTO>;
  lapsi: string;
  maksun_peruste_koodi: string;
  palveluseteli_arvo: string; // float number
  asiakasmaksu: string; // float number
  perheen_koko: number;
  alkamis_pvm: string; // YYYY-MM-dd
  paattymis_pvm?: string; // YYYY-MM-dd
  tallennetut_huoltajat_count: number;
  ei_tallennetut_huoltajat_count: number;
  lahdejarjestelma?: Lahdejarjestelma;
}

export class HuoltajaDTO {
  henkilo_oid?: string;
  etunimet?: string;
  sukunimi?: string;
  henkilotunnus?: string;
}

export class VardaCreateMaksutietoDTO {
  huoltajat: Array<HuoltajaDTO>;
  lapsi: string;
  palveluseteli_arvo: number;
  perheen_koko: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  maksun_peruste_koodi: string;
  asiakasmaksu: number;
}

export class VardaUpdateMaksutietoDTO {
  paattymis_pvm: string;
}
