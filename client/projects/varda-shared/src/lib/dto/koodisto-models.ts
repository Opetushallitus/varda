export enum KoodistoEnum {
  kunta = 'kunta',
  kieli = 'kielikoodistoopetushallinto',
  jarjestamismuoto = 'vardajarjestamismuoto',
  toimintamuoto = 'vardatoimintamuoto',
  kasvatusopillinenjarjestelma = 'vardakasvatusopillinenjarjestelma',
  toiminnallinenpainotus = 'vardatoiminnallinenpainotus',
  tyosuhde = 'vardatyosuhde',
  tyoaika = 'vardatyoaika',
  tehtavanimike = 'vardatehtavanimike',
  sukupuoli = 'sukupuoli',
  tutkinto = 'vardatutkinto',
  maksunperuste = 'vardamaksunperuste',
  lahdejarjestelma = 'vardalahdejarjestelma',
}

export interface KoodistoDTO {
  name: KoodistoEnum;
  version: number;
  update_datetime: string;
  codes: Array<CodeDTO>;
}

export interface CodeDTO {
  code_value: string;
  name: string;
  description: string;
}

export enum KoodistoSortBy {
  name = 'name',
  codeValue = 'code_value'
}
