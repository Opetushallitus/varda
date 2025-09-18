export class PaosToimintaCreateDto {
  paos_organisaatio?: string;
  oma_organisaatio?: string;
  paos_toimipaikka?: string;
}

export class PaosToimintaDto extends PaosToimintaCreateDto {
  id: string;
  voimassa_kytkin: boolean;
}

// Fields optional because typescript can't understand one of two classes so we need union for abstract class using generics.
export class PaosToimintatietoDto {
  paos_oikeus?: PaosOikeusTieto;
  paos_toiminta_id?: string;
  url?: string;
  vakajarjestaja_id?: number;
  vakajarjestaja_nimi?: string;
  vakajarjestaja_organisaatio_oid?: string;
  vakajarjestaja_url?: string;
}

export class PaosOikeusTieto {
  id: number;
  tallentaja_organisaatio_id: number;
  tallentaja_organisaatio_oid: string;
  voimassa_kytkin: boolean;
}

// Fields optional because typescript can't understand one of two classes so we need union for abstract class using generics.
export class PaosToimipaikkatietoDto {
  paos_oikeus?: PaosOikeusTieto;
  paos_toiminta_id?: string;
  toimija_id?: number;
  toimija_organisaatio_oid?: string;
  toimija_y_tunnus?: string;
  toimija_nimi?: string;
  toimija_url?: string;
  toimipaikka_id?: number;
  toimipaikka_nimi?: string;
  toimipaikka_organisaatio_oid?: string;
  toimipaikka_url?: string;
}

export class PaosToimijaInternalDto {
  paosOikeus: PaosOikeusTieto;
  toimijaUrl?: string;
  toimijaId?: number;
  toimijaOID?: string;
  toimijaNimi?: string;
  toimijaYTunnus?: string;
  toimipaikat: Array<PaosToimipaikkatietoDto>;
}

export class PaosVakajarjestajaDto {
  id: number;
  url: string;
  nimi: string;
  y_tunnus: string;
  organisaatio_oid: string;
  kunnallinen_kytkin: boolean;
}

export class PaosToimipaikkaDto {
  id: number;
  url: string;
  nimi: string;
  organisaatio_oid: string;
}
