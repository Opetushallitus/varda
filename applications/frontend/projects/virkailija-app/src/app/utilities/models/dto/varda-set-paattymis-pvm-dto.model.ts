export interface VardaSetPaattymisPvmDTO {
  status: string;
  toimipaikka: number;
  kielipainotus: number;
  toiminnallinenpainotus: number;
  varhaiskasvatuspaatos: number;
  varhaiskasvatussuhde: number;
  maksutieto: number;
  palvelussuhde: number;
  tyoskentelypaikka: number;
}

export interface VardaSetPaattymisPvmPostDTO {
  vakajarjestaja_oid: string;
  paattymis_pvm: string;
}

export interface VardaSetPaattymisPvmPostResultDTO {
  identifier: string;
}
