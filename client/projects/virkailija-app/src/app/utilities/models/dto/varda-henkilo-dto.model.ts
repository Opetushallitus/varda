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
  henkilo_oid: string;
  tyontekijat?: Array<TyontekijaListDTO>;
  lapset?: Array<LapsiListDTO>;
  expanded?: boolean;
}
