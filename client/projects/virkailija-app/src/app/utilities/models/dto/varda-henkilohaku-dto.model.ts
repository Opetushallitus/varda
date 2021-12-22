import {VardaHenkiloDTO} from './varda-henkilo-dto.model';

export class HenkilohakuResultDTO {
  id: number;
  url: string;
  henkilo: VardaHenkiloDTO;
  maksutiedot: Array<string>;
  toimipaikat: Array<{nimi: string; nimi_sv: string; organisaatio_oid: string }>;
}

export enum HenkilohakuType {
  lapset = 'lapset',
  tyontekija = 'tyontekijat',
}

export enum FilterStatus {
  kaikki = 'kaikki',
  voimassaOlevat = 'voimassaolevat',
  paattyneet = 'paattyneet',
  eiMaksutietoja = 'eimaksutietoja'
}

export enum FilterObject {
  vakapaatokset = 'vakapaatokset',
  vakasuhteet = 'vakasuhteet',
  maksutiedot = 'maksutiedot'
}

export class HenkilohakuSearchDTO {
  search: string;
  type: HenkilohakuType;
  filter_status: FilterStatus;
  filter_object: FilterObject;
  page?: number;
}

export class LapsiByToimipaikkaDTO {
  etunimet: string;
  sukunimi: string;
  syntyma_pvm: string;
  henkilo_oid: string;
  oma_organisaatio_nimi: string;
  paos_organisaatio_nimi: string;
  lapsi_id: number;
  lapsi_url: string;
}

export class LapsiKooste {
  id?: number;
  yksityinen_kytkin: boolean;
  henkilo: LapsiKoosteHenkilo;
  varhaiskasvatuspaatokset: Array<LapsiKoosteVakapaatos>;
  varhaiskasvatussuhteet: Array<LapsiKoosteVakasuhde>;
  maksutiedot: Array<LapsiKoosteMaksutieto>;
  oma_organisaatio_nimi?: string;
  paos_organisaatio_nimi?: string;
}

export class LapsiKoosteHenkilo {
  etunimet: string;
  kutsumanimi: string;
  sukunimi: string;
  id: number;
  henkilo_oid: string;
  syntyma_pvm: string;
  turvakielto: boolean;
}

export class LapsiKoosteHuoltaja {
  henkilo_oid: string;
  etunimet: string;
  sukunimi: string;
}

export class LapsiKoosteMaksutieto {
  id: number;
  maksun_peruste_koodi: string;
  palveluseteli_arvo: number;
  asiakasmaksu: number;
  perheen_koko: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  huoltajat: Array<LapsiKoosteHuoltaja>;
}

export class LapsiKoosteVakapaatos {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  hakemus_pvm: string;
  tuntimaara_viikossa: number;
  jarjestamismuoto_koodi: string;
  paivittainen_vaka_kytkin: boolean;
  kokopaivainen_vaka_kytkin: boolean;
  vuorohoito_kytkin: boolean;
  pikakasittely_kytkin: boolean;
}

export class LapsiKoosteVakasuhde {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  toimipaikka_nimi: string;
  varhaiskasvatuspaatos: string;
}

export class TyontekijaByToimipaikkaDTO {
  etunimet: string;
  sukunimi: string;
  henkilo_oid: string;
  vakajarjestaja_nimi: string;
  tyontekija_id: number;
  tyontekija_url: string;
}

export class TyontekijaKooste {
  id: number;
  vakajarjestaja_id: number;
  vakajarjestaja_nimi: string;
  tutkinnot: Array<TyontekijaTutkinto>;
  henkilo: TyontekijaHenkilo;
  taydennyskoulutukset: Array<TyontekijaTaydennyskoulutus>;
  palvelussuhteet: Array<TyontekijaPalvelussuhde>;
}

export class TyontekijaTutkinto {
  id: number;
  tutkinto_koodi: string;
}

export class TyontekijaHenkilo {
  id: number;
  etunimet: string;
  sukunimi: string;
  henkilo_oid: string;
  turvakielto: string;
}

export class TyontekijaTaydennyskoulutusCombined {
  id: number;
  tehtavanimikeList: Array<string>;
  nimi: string;
  suoritus_pvm: string;
  koulutuspaivia: number;
}

export class TyontekijaTaydennyskoulutus {
  id: number;
  tehtavanimike_koodi: string;
  nimi: string;
  suoritus_pvm: string;
  koulutuspaivia: number;
}

export class TyontekijaPalvelussuhde {
  id: number;
  tyosuhde_koodi: string;
  tyoaika_koodi: string;
  tyoaika_viikossa: number;
  tutkinto_koodi: string;
  alkamis_pvm: string;
  paattymis_pvm: string;
  tyoskentelypaikat: Array<TyontekijaTyoskentelypaikka>;
  pidemmatpoissaolot: Array<TyontekijaPidempiPoissaolo>;
}

export class TyontekijaTyoskentelypaikka {
  id: number;
  toimipaikka_id: number;
  toimipaikka_nimi: string;
  tehtavanimike_koodi: string;
  kelpoisuus_kytkin: boolean;
  kiertava_tyontekija_kytkin: boolean;
  alkamis_pvm: string;
  paattymis_pvm: string;
}

export class TyontekijaPidempiPoissaolo {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
}
