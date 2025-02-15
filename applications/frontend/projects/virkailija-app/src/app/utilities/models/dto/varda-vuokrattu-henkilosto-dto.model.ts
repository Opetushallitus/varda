import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaVuokrattuHenkilostoDTO {
  id?: number;
  kuukausi: string;
  lahdejarjestelma: Lahdejarjestelma;
  muutos_pvm?: string;
  tunniste?: string;
  tuntimaara: string;
  tyontekijamaara: number;
  url?: string;
  vakajarjestaja?: string;
  vakajarjestaja_oid: string;
}
