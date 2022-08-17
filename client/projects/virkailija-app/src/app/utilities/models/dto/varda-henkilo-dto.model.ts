import { TyontekijaListDTO } from './varda-tyontekija-dto.model';
import { LapsiListDTO } from './varda-lapsi-dto.model';
import { PuutteellinenErrorDTO } from './varda-puutteellinen-dto.model';

export class VardaHenkiloDTO {
  id?: number;
  url?: string;
  etunimet?: string;
  sukunimi?: string;
  kutsumanimi?: string;
  syntyma_pvm?: string;
  henkilo_oid?: string;
  turvakielto?: boolean;
  lapsi?: Array<string>;
  tyontekija?: Array<string>;
  mock?: boolean;
}

export interface HenkiloListDTO {
  id: number;
  url: string;
  etunimet: string;
  sukunimi: string;
  henkilo_id: number;
  henkilo_oid: string;
  tyontekijat?: Array<TyontekijaListDTO>;
  lapset?: Array<LapsiListDTO>;
  expanded?: boolean;
  lapsi_id?: number;
  tyontekija_id?: number;
  errors?: Array<PuutteellinenErrorDTO>;
}
