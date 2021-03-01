import { Hallinnointijarjestelma, Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaToimipaikkaDTO {
  lahdejarjestelma?: Lahdejarjestelma;
  id?: number;
  url?: string;
  vakajarjestaja?: string;
  nimi?: string;
  oid?: string;
  organisaatio_oid?: string;
  katuosoite?: string;
  postiosoite?: string;
  postitoimipaikka?: string;
  postinumero?: string;
  kunta_koodi?: string;
  puhelinnumero?: string;
  sahkopostiosoite?: string;
  kasvatusopillinen_jarjestelma_koodi?: string;
  toimintamuoto_koodi?: string;
  asiointikieli_koodi?: Array<string>;
  jarjestamismuoto_koodi?: Array<string>;
  varhaiskasvatuspaikat?: number;
  kielipainotus_kytkin?: boolean;
  toiminnallinenpainotus_kytkin?: boolean;
  toimipaikka?: VardaToimipaikkaDTO;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
  muutos_pvm?: string;
  hallinnointijarjestelma?: Hallinnointijarjestelma;
  paos_toimipaikka_kytkin?: boolean;
  paos_oma_organisaatio_url?: string;
  paos_organisaatio_url?: string;
  paos_organisaatio_nimi?: string;
  kayntiosoite?: string;
  kayntiosoite_postinumero?: string;
  kayntiosoite_postitoimipaikka?: string;
}

export class VardaToimipaikkaMinimalDto {
  id?: number;
  hallinnointijarjestelma: Hallinnointijarjestelma;
  nimi: string;
  nimi_original: string;
  organisaatio_oid: string;
  paos_tallentaja_organisaatio_id_list?: Array<number>;
  paos_oma_organisaatio_url?: string;
  paos_organisaatio_nimi?: string;
  paos_organisaatio_url?: string;
  paos_toimipaikka_kytkin: boolean;
  url: string;
}

export class VardaToimipaikkaSearchDto {
  search: string;
}

export class ToimipaikkaKooste {
  id: number;
  vakajarjestaja_id: number;
  vakajarjestaja_nimi: string;
  kielipainotukset: Array<KielipainotusDTO>;
  toiminnalliset_painotukset: Array<ToiminnallinenPainotusDTO>;
  nimi: string;
  nimi_sv: string;
  organisaatio_oid: string;
  kayntiosoite: string;
  kayntiosoite_postinumero: string;
  kayntiosoite_postitoimipaikka: string;
  postiosoite: string;
  postinumero: string;
  postitoimipaikka: string;
  kunta_koodi: string;
  puhelinnumero: string;
  sahkopostiosoite: string;
  kasvatusopillinen_jarjestelma_koodi: string;
  toimintamuoto_koodi: string;
  asiointikieli_koodi: Array<string>;
  jarjestamismuoto_koodi: Array<string>;
  varhaiskasvatuspaikat: number;
  toiminnallinenpainotus_kytkin: boolean;
  kielipainotus_kytkin: boolean;
  alkamis_pvm: string;
  paattymis_pvm: string;
  hallinnointijarjestelma: string;
}

export class KielipainotusDTO {
  lahdejarjestelma?: Lahdejarjestelma;
  id: number;
  url?: string;
  toimipaikka?: string;
  kielipainotus_koodi?: string;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
}

export class ToiminnallinenPainotusDTO {
  lahdejarjestelma?: Lahdejarjestelma;
  id: number;
  url?: string;
  toimipaikka?: string;
  toimintapainotus_koodi?: string;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
}
