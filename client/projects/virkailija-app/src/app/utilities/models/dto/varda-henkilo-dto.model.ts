export class VardaHenkiloDTO {
  id?: number;
  url?: string;
  etunimet?: string;
  sukunimi?: string;
  syntyma_pvm?: string;
  henkilo_oid?: string;
  lapsi?: Array<string>;
  tyontekija?: Array<string>;
}
