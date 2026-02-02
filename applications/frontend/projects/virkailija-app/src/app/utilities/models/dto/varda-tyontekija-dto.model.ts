import { HenkiloRooliEnum } from '../enums/henkilorooli.enum';
import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaTyontekijaDTO {
  id: number;
  url: string;
  henkilo: string;
  henkilo_oid: string;
  vakajarjestaja: string;
  vakajarjestaja_oid: string;
  sahkopostiosoite: string | null;
  lahdejarjestelma: Lahdejarjestelma;
  tunniste: string | null;
  muutos_pvm: string;
}

export interface TyontekijaListDTO {
  id?: number;
  url?: string;
  henkilo_id?: number;
  henkilo_oid?: string;
  rooli: HenkiloRooliEnum;
  is_missing_data?: boolean;
  tehtavanimikkeet?: Array<string>;
  etunimet?: string;
  sukunimi?: string;
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

export class VardaPalvelussuhdeDTO {
  id: number;
  url: string;
  tyontekija: string;
  tyontekija_tunniste: string | null;
  tyoaika_koodi: string;
  tyoaika_viikossa: number;
  tutkinto_koodi: string;
  tyosuhde_koodi: string;
  alkamis_pvm: string;
  paattymis_pvm: string | null;
  lahdejarjestelma: Lahdejarjestelma;
  tunniste: string | null;
  muutos_pvm: string;
  luonti_pvm: string;
}

export class VardaTyoskentelypaikkaDTO {
  id: number;
  url: string;
  palvelussuhde: string;
  palvelussuhde_tunniste: string | null;
  toimipaikka: string;
  toimipaikka_oid: string;
  kiertava_tyontekija_kytkin: boolean;
  kelpoisuus_kytkin: boolean;
  tehtavanimike_koodi: string;
  alkamis_pvm: string;
  paattymis_pvm: string | null;
  lahdejarjestelma: Lahdejarjestelma;
  tunniste: string | null;
  muutos_pvm: string;
  luonti_pvm: string;
}

export class VardaPidempiPoissaoloDTO {
  id: number;
  url: string;
  palvelussuhde: string;
  palvelussuhde_tunniste: string | null;
  alkamis_pvm: string;
  paattymis_pvm: string | null;
  lahdejarjestelma: Lahdejarjestelma;
  tunniste: string | null;
  muutos_pvm: string;
  luonti_pvm: string;
}

export interface VardaTutkintoDTO {
  id: number;
  url: string;
  henkilo: string;
  henkilo_oid: string;
  tutkinto_koodi: string;
  muutos_pvm: string;
}
