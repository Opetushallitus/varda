import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export interface VardaTaydennyskoulutusDTO {
  id?: string;
  url?: string;
  nimi?: string;
  suoritus_pvm?: string;
  koulutuspaivia?: number;
  taydennyskoulutus_tyontekijat?: Array<VardaTaydennyskoulutusTyontekijaDTO>;
  taydennyskoulutus_tyontekijat_add?: Array<VardaTaydennyskoulutusTyontekijaDTO>;
  taydennyskoulutus_tyontekijat_remove?: Array<VardaTaydennyskoulutusTyontekijaDTO>;
  taydennyskoulutus_tyontekijat_count?: number;
  muutos_pvm?: string;
  lahdejarjestelma?: Lahdejarjestelma;
  tunniste?: string;
  osallistuja_lkm?: number;
}

export interface VardaTaydennyskoulutusTyontekijaDTO {
  tyontekija?: string;
  tehtavanimike_koodi: string;
  henkilo_oid?: string;
  vakajarjestaja_oid?: string;
  lahdejarjestelma?: Lahdejarjestelma;
}


export interface VardaTaydennyskoulutusTyontekijaListDTO {
  tehtavanimike_koodit: Array<string>;
  henkilo_etunimet?: string;
  henkilo_sukunimi?: string;
  henkilo_oid: string;
  nimi?: string;
  valitut_nimikkeet?: Array<string>;
}
