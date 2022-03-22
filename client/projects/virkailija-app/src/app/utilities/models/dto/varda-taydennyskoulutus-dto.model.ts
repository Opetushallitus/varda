import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export interface VardaTaydennyskoulutusDTO {
  id: number;
  url: string;
  nimi: string;
  suoritus_pvm: string;
  koulutuspaivia: number;
  taydennyskoulutus_tyontekijat: Array<VardaTaydennyskoulutusTyontekijaDTO>;
  taydennyskoulutus_tyontekijat_count: number;
  lahdejarjestelma: Lahdejarjestelma;
  tunniste: string | null;
  muutos_pvm: string;
}

export interface VardaTaydennyskoulutusSaveDTO {
  id?: number;
  nimi?: string;
  suoritus_pvm?: string;
  koulutuspaivia?: number;
  taydennyskoulutus_tyontekijat?: Array<VardaTaydennyskoulutusTyontekijaSaveDTO>;
  taydennyskoulutus_tyontekijat_add?: Array<VardaTaydennyskoulutusTyontekijaSaveDTO>;
  taydennyskoulutus_tyontekijat_remove?: Array<VardaTaydennyskoulutusTyontekijaSaveDTO>;
  lahdejarjestelma?: Lahdejarjestelma;
  tunniste?: string | null;
}

export interface VardaTaydennyskoulutusTyontekijaDTO {
  tehtavanimike_koodi: string;
  tyontekija: string;
  henkilo_oid: string;
  vakajarjestaja: string;
  vakajarjestaja_oid: string;
  lahdejarjestelma: Lahdejarjestelma;
  tunniste: string | null;
}

export interface VardaTaydennyskoulutusTyontekijaSaveDTO {
  tehtavanimike_koodi: string;
  tyontekija?: string;
  henkilo_oid?: string;
  vakajarjestaja?: string;
  vakajarjestaja_oid?: string;
  lahdejarjestelma?: Lahdejarjestelma;
  tunniste?: string | null;
}

export interface VardaTaydennyskoulutusTyontekijaListDTO {
  tehtavanimike_koodit: Array<string>;
  henkilo_etunimet?: string;
  henkilo_sukunimi?: string;
  henkilo_oid: string;
  nimi?: string;
  valitut_nimikkeet?: Array<string>;
}
