import { HenkiloRooliEnum } from '../enums/henkilorooli.enum';

export class VardaLapsiCreateDto {
  public constructor(init?: Partial<VardaLapsiCreateDto>) {
    Object.assign(this, init);
  }

  henkilo?: string;
  vakatoimija?: string;
  oma_organisaatio?: string;
  paos_organisaatio?: string;
}

export class VardaLapsiDTO extends VardaLapsiCreateDto {
  url?: string;
  id: number;
  oma_organisaatio_oid?: string;
  paos_organisaatio_oid?: string;
}


export interface LapsiListDTO {
  id: number;
  url: string;
  henkilo_id: number;
  henkilo_oid: string;
  rooli: HenkiloRooliEnum;
  vakatoimija_oid: string;
  vakatoimija_nimi: string;
  oma_organisaatio_oid: string;
  oma_organisaatio_nimi: string;
  paos_organisaatio_oid: string;
  paos_organisaatio_nimi: string;
  toimipaikat: Array<LapsiListToimipaikkaDTO>;
}

export interface LapsiListToimipaikkaDTO {
  id: number;
  url: string;
  organisaatio_oid: string;
  nimi: string;
}
