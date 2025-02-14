export class VardaKoodistoDto {
  koodiUri: string;
  koodiArvo: string;
  metadata: Array<VardaKoodistoMetadataDto>;
  voimassaAlkuPvm: string;
  voimassaLoppuPvm: string;
}

export class VardaKoodistoMetadataDto {
  kieli: string;
  nimi: string;
}

