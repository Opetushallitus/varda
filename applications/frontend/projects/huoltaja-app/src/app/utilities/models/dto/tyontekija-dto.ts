export interface TyontekijatiedotDTO {
  tyontekijat: Array<TyontekijaDTO>;
}

export interface TyontekijaDTO {
  id: number;
  aktiivinen_toimija: boolean;
  vakajarjestaja_id: number;
  vakajarjestaja_oid: string;
  vakajarjestaja_nimi: string;
  tutkinnot: Array<TutkintoDTO>;
  palvelussuhteet: Array<PalvelussuhdeDTO>;
  taydennyskoulutukset: Array<TaydennyskoulutusDTO>;
  yhteysosoite: string;
}

export interface TutkintoDTO {
  id: number;
  tutkinto_koodi: string;
}

export interface TyoskentelypaikkaDTO {
  id: number;
  toimipaikka_id: number;
  toimipaikka_oid: string;
  toimipaikka_nimi: string;
  tehtavanimike_koodi: string;
  kelpoisuus_kytkin: boolean;
  kiertava_tyontekija_kytkin: boolean;
  alkamis_pvm: string;
  paattymis_pvm?: any;
}

export interface PoissaoloDTO {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm: string;
}

export interface PalvelussuhdeDTO {
  id: number;
  tyosuhde_koodi: string;
  tyoaika_koodi: string;
  tyoaika_viikossa: string;
  tutkinto_koodi: string;
  alkamis_pvm: string;
  paattymis_pvm?: any;
  tyoskentelypaikat: Array<TyoskentelypaikkaDTO>;
  pidemmat_poissaolot: Array<PoissaoloDTO>;
}

export interface TaydennyskoulutusDTO {
  id: number;
  koulutuspaivia: number;
  nimi: string;
  suoritus_pvm: string;
  tehtavanimike_koodi_list: Array<string>;
}

