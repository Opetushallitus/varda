import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaPoissaoloDTO {
  id?: number;
  url?: string;
  lahdejarjestelma?: Lahdejarjestelma;
  toimipaikka?: string;
  toimipaikka_oid?: string;
  palvelussuhde?: string;
  palvelussuhde_tunniste?: string;
  tunniste?: string;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
}
