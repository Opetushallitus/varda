import { HenkiloRooliEnum } from '../enums/henkilorooli.enum';
import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaTyontekijaDTO {
  id?: number;
  url?: string;
  toimipaikka?: string;
  toimipaikka_oid?: string;
  henkilo?: string;
  henkilo_oid?: string;
  vakajarjestaja?: string;
  vakajarjestaja_oid?: string;
  lahdejarjestelma?: Lahdejarjestelma;
  tunniste?: string;
  muutos_pvm?: string;
}


export interface TyontekijaListDTO {
  id?: number;
  url?: string;
  henkilo_id?: number;
  henkilo_oid?: string;
  rooli: HenkiloRooliEnum;
  tyoskentelypaikat?: Array<TyontekijaListTyoskentelypaikkaDTO>;
  tehtavanimikkeet?: Array<string>;
}

export interface TyontekijaListTyoskentelypaikkaDTO {
  id: number;
  url: string;
  toimipaikka_oid: string;
  toimipaikka_nimi: string;
  kiertava_tyontekija_kytkin: boolean;
  tehtavanimike_koodi: string;
  alkamis_pvm: string;
}
