import { TyontekijaListDTO } from './varda-tyontekija-dto.model';
import { LapsiListDTO } from './varda-lapsi-dto.model';

export class VardaHenkiloDTO {
  id?: number;
  url?: string;
  etunimet?: string;
  sukunimi?: string;
  kutsumanimi?: string;
  syntyma_pvm?: string;
  henkilo_oid?: string;
  lapsi?: Array<string>;
  tyontekija?: Array<string>;
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
  errors?: Array<HenkiloListErrorDTO>;
}


export interface HenkiloListErrorDTO {
  description: string;
  error_code: string;
  model_id_list: Array<number>;
  model_name: string;
}
