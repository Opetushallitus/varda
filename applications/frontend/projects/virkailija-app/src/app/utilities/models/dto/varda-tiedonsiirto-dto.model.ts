export interface VardaTiedonsiirtoDTO {
  request_url: string;
  request_method: string;
  request_body: string;
  response_code: number;
  response_body: string;
  lahdejarjestelma: string;
  target: VardaTiedonsiirtoTargetDTO;
  user_id: number;
  username: string;
  vakajarjestaja_id: number;
  vakajarjestaja_name: string;
  timestamp: string;

  response_list?: Array<TiedonsiirtoResponseList>;
}

export interface VardaTiedonsiirtoTargetDTO {
  tyontekija_id: number;
  henkilo_oid: string;
  etunimet: string;
  sukunimi: string;
}

export interface TiedonsiirtoResponseList {
  field: string;
  error_code: string;
  expand?: boolean;
}


export interface VardaTiedonsiirtoYhteenvetoDTO {
  date: string;
  successful: number;
  unsuccessful: number;
  user_id: number;
  username: string;
}
