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

export interface LapsiByToimipaikkaDTO {
  etunimet: string;
  sukunimi: string;
  syntyma_pvm: string;
  henkilo_oid: string;
  oma_organisaatio_nimi: string;
  paos_organisaatio_nimi: string;
  lapsi_id: number;
  lapsi_url: string;
}

export interface LapsiKooste {
  id: number;
  yksityinen_kytkin: boolean;
  henkilo: LapsiKoosteHenkilo;
  varhaiskasvatuspaatokset: Array<LapsiKoosteVakapaatos>;
  maksutiedot: Array<LapsiKoosteMaksutieto>;
  vakatoimija_id: number | null;
  vakatoimija_oid: string | null;
  vakatoimija_nimi: string | null;
  oma_organisaatio_id: number | null;
  oma_organisaatio_oid: string | null;
  oma_organisaatio_nimi: string | null;
  paos_organisaatio_id: number | null;
  paos_organisaatio_oid: string | null;
  paos_organisaatio_nimi: string | null;
  tallentaja_organisaatio_oid: string | null;
  muutos_pvm: string;
  luonti_pvm: string;
}

export interface LapsiKoosteRaw extends Omit<LapsiKooste, 'varhaiskasvatuspaatokset'> {
  varhaiskasvatuspaatokset: Array<LapsiKoosteVakapaatosRaw>;
  varhaiskasvatussuhteet: Array<LapsiKoosteVakasuhde>;
}

export interface LapsiKoosteHenkilo {
  id: number;
  etunimet: string;
  kutsumanimi: string;
  sukunimi: string;
  henkilo_oid: string;
  syntyma_pvm: string;
  turvakielto: boolean;
}

export interface LapsiKoosteHuoltaja {
  henkilo_oid: string;
  etunimet: string;
  sukunimi: string;
}

export interface LapsiKoosteMaksutieto {
  id: number;
  maksun_peruste_koodi: string;
  palveluseteli_arvo: string;
  asiakasmaksu: string;
  perheen_koko: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  huoltajat: Array<LapsiKoosteHuoltaja>;
  muutos_pvm: string;
  luonti_pvm: string;
}

export interface LapsiKoosteVakapaatos {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  hakemus_pvm: string;
  tuntimaara_viikossa: number;
  jarjestamismuoto_koodi: string;
  tilapainen_vaka_kytkin: boolean;
  paivittainen_vaka_kytkin: boolean;
  kokopaivainen_vaka_kytkin: boolean;
  vuorohoito_kytkin: boolean;
  pikakasittely_kytkin: boolean;
  varhaiskasvatussuhteet: Array<LapsiKoosteVakasuhde>;
  muutos_pvm: string;
  luonti_pvm: string;
}

export type LapsiKoosteVakapaatosRaw = Omit<LapsiKoosteVakapaatos, 'varhaiskasvatussuhteet'>;

export interface LapsiKoosteVakasuhde {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  toimipaikka: string;
  toimipaikka_oid: string;
  toimipaikka_nimi: string;
  varhaiskasvatuspaatos: string;
  muutos_pvm: string;
  luonti_pvm: string;
}

export interface TyontekijaByToimipaikkaDTO {
  etunimet: string;
  sukunimi: string;
  henkilo_oid: string;
  vakajarjestaja_nimi: string;
  tyontekija_id: number;
  tyontekija_url: string;
}

export interface TyontekijaKooste {
  id: number;
  vakajarjestaja_id: number;
  vakajarjestaja_nimi: string;
  sahkopostiosoite: string | null;
  tutkinnot: Array<TyontekijaTutkinto>;
  henkilo: TyontekijaHenkilo;
  taydennyskoulutukset: Array<TyontekijaTaydennyskoulutus>;
  palvelussuhteet: Array<TyontekijaPalvelussuhde>;
}

export interface TyontekijaKoosteRaw extends Omit<TyontekijaKooste, 'taydennyskoulutukset'> {
  taydennyskoulutukset: Array<TyontekijaTaydennyskoulutusRaw>;
}

export interface TyontekijaTutkinto {
  id: number;
  tutkinto_koodi: string;
}

export interface TyontekijaHenkilo {
  id: number;
  etunimet: string;
  sukunimi: string;
  henkilo_oid: string;
  turvakielto: string;
  luonti_pvm: string;
  muutos_pvm: string;
}

export interface TyontekijaTaydennyskoulutus {
  id: number;
  tehtavanimikeList: Array<string>;
  nimi: string;
  suoritus_pvm: string;
  koulutuspaivia: number;
  contains_other_tyontekija: boolean;
  read_only?: boolean;
  luonti_pvm: string;
  muutos_pvm: string;
}

export interface TyontekijaTaydennyskoulutusRaw extends Omit<TyontekijaTaydennyskoulutus, 'tehtavanimikeList'> {
  tehtavanimike_koodi: string;
}

export interface TyontekijaPalvelussuhde {
  id: number;
  tyosuhde_koodi: string;
  tyoaika_koodi: string;
  tyoaika_viikossa: number;
  tutkinto_koodi: string;
  alkamis_pvm: string;
  paattymis_pvm: string;
  tyoskentelypaikat: Array<TyontekijaTyoskentelypaikka>;
  pidemmatpoissaolot: Array<TyontekijaPidempiPoissaolo>;
  luonti_pvm: string;
  muutos_pvm: string;
}

export interface TyontekijaTyoskentelypaikka {
  id: number;
  toimipaikka_id: number;
  toimipaikka_oid: string;
  toimipaikka_nimi: string;
  tehtavanimike_koodi: string;
  kelpoisuus_kytkin: boolean;
  kiertava_tyontekija_kytkin: boolean;
  alkamis_pvm: string;
  paattymis_pvm: string;
  luonti_pvm: string;
  muutos_pvm: string;
}

export interface TyontekijaPidempiPoissaolo {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
  luonti_pvm: string;
  muutos_pvm: string;
}
