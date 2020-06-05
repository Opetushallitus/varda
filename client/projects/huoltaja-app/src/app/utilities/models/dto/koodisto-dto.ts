export class KoodistoDto {
  koodiUri: string;
  koodiArvo: string;
  metadata: Array<KoodistoMetadataDto>;
  voimassaAlkuPvm: string;
  voimassaLoppuPvm: string;
}

export class KoodistoMetadataDto {
  kieli: string;
  nimi: string;
}
