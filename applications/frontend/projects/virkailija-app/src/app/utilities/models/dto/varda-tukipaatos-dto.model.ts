import {Lahdejarjestelma} from "../enums/hallinnointijarjestelma";

export class VardaTukipaatosDTO {
  id?: number;
  vakajarjestaja?: string;
  vakajarjestaja_oid: string;
  paatosmaara: number;
  yksityinen_jarjestaja: boolean;
  ikaryhma_koodi: string;
  tuentaso_koodi: string;
  tilastointi_pvm?: string;
  muutos_pvm?: string;
  lahdejarjestelma: Lahdejarjestelma;
  tunniste?: string;
}

export interface Aikavali {
  alkamis_pvm: string;
  paattymis_pvm: string;
  tilastointi_pvm: string;
}

export class VardaTukipaatosListsDTO {
  ikaryhma_koodi_list: Array<string>;
  tuentaso_koodi_list: Array<string>;
  tilastointi_pvm_list: Array<string>;
  next_aikavali: Aikavali;
}
