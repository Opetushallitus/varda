export interface VardaYksiloimatonDTO {
  id: number;
  henkilo_oid: string;
  organisaatio_oid: string;
}


export interface YksiloimatonSearchFilter {
  page?: number;
  count?: number;
  page_size?: number;
  vakatoimija_oid?: string;
}
