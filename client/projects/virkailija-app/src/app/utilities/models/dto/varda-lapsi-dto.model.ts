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
  oma_organisaatio_nimi?: string;
  paos_organisaatio_nimi?: string;
}
