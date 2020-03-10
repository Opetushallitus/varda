import {Lahdejarjestelma} from '../enums/lahdejarjestelma';

export class VardaToimipaikkaDTO {
  id?: string;
  url?: string;
  vakajarjestaja?: string;
  nimi?: string;
  oid?: string;
  organisaatio_oid?: string;
  katuosoite?: string;
  postitoimipaikka?: string;
  postinumero?: string;
  kunta_koodi?: string;
  puhelinnumero?: string;
  sahkopostiosoite?: string;
  kasvatusopillinen_jarjestelma_koodi?: string;
  toimintamuoto_koodi?: string;
  asiointikieli_koodi?: any;
  jarjestamismuoto_koodi?: any;
  varhaiskasvatuspaikat?: any;
  kielipainotus_kytkin?: boolean;
  toiminnallinenpainotus_kytkin?: boolean;
  toimipaikka?: VardaToimipaikkaDTO;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
  lahdejarjestelma?: Lahdejarjestelma;
  paos_toimipaikka_kytkin?: boolean;
  paos_oma_organisaatio_url?: string;
  paos_organisaatio_url?: string;
  paos_organisaatio_nimi?: string;
}

export class VardaToimipaikkaMinimalDto {
  id?: string;
  lahdejarjestelma: Lahdejarjestelma;
  nimi: string;
  organisaatio_oid: string;
  paos_oma_organisaatio_url?: string;
  paos_organisaatio_nimi?: string;
  paos_organisaatio_url?: string;
  paos_toimipaikka_kytkin: boolean;
  url: string;
}

export class VardaToimipaikkaSearchDto {
  search: string;
}
