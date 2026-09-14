export interface VardaYksiloimatonDTO {
  id: number;
  henkilo_oid: string;
  organisaatio_oid: string;
}


export interface YksiloimatonSearchFilter {
  cursor?: string | null;
  count?: number;
  page_size?: number;
  vakatoimija_oid?: string;
}
