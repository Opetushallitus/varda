export interface HenkiloDTO {
  henkilo_oid?: string;
  henkilotunnus?: string;
  etunimet?: string;
  kutsumanimi?: string;
  sukunimi?: string;
  aidinkieli_koodi?: string;
  sukupuoli_koodi?: string;
  syntyma_pvm?: string;
  kotikunta_koodi?: string;
  katuosoite?: string;
  postinumero?: string;
  postitoimipaikka?: string;
  muut_osoitteet?: Array<string>;
  toggle_expanded?: boolean;
}
