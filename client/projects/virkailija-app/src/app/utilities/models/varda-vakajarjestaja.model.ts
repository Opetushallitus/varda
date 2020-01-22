
export class VardaVakajarjestaja {
  id: string;
  url?: string;
  nimi?: string;
  y_tunnus?: string;
  oid?: string;
  organisaatio_oid?: string;
  kunta_koodi?: string;
  sahkopostiosoite?: string;
  tilinumero?: string;
  ip_osoite?: string;
  katuosoite?: string;
  postitoimipaikka?: string;
  postinumero?: string;
  puhelinnumero?: string;
  alkamis_pvm?: string;
  paattymis_pvm?: string;
  muutos_pvm?: string;
  kunnallinen_kytkin?: boolean;
}

export class AllVakajarjestajaSearchDto {
  tyyppi?: 'kunnallinen' | 'yksityinen';
  search?: string;
}
