import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaPalvelussuhdeDTO {
  id?: string;
  tunniste?: string;
  url?: string;
  tyontekija?: string;
  tyontekija_tunniste?: string;
  toimipaikka: string;
  toimipaikka_oid: string;
  vakituinen_kytkin?: boolean;
  tyoaika_koodi: string;
  tyoaika_viikossa?: number;
  tutkinto_koodi?: string;
  tyosuhde_koodi?: string;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
  muutos_pvm?: string;
  tyoskentelypaikat?: Array<string>;
  poissaolot?: Array<string>;
  lahdejarjestelma?: Lahdejarjestelma;
}
