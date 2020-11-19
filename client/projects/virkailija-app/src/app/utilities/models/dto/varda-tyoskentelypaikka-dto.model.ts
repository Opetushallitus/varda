import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaTyoskentelypaikkaDTO {
  id?: number;
  url?: string;
  palvelussuhde?: string;
  palvelussuhde_tunniste?: string;
  toimipaikka: string;
  toimipaikka_oid: string;
  kiertava_tyontekija_kytkin?: boolean;
  kelpoisuus_kytkin?: boolean;
  tehtavanimike_koodi?: string;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
  toimipaikka_nimi?: string;
  lahdejarjestelma?: Lahdejarjestelma;
  tunniste?: string;
}
