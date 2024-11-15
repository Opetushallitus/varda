export interface PuutteellinenErrorDTO {
  description: string;
  error_code: string;
  model_id_list: Array<number>;
  model_name: string;
}

export class PuutteellinenToimipaikkaListDTO {
  toimipaikka_id: number;
  organisaatio_oid: string;
  nimi: string;
  errors?: Array<PuutteellinenErrorDTO>;
}

export class PuutteellinenOrganisaatioListDTO {
  organisaatio_id: number;
  organisaatio_oid: string;
  nimi: string;
  errors?: Array<PuutteellinenErrorDTO>;
}

export class PuutteellinenErrorsDTO {
  error_codes: Array<string>;
}
