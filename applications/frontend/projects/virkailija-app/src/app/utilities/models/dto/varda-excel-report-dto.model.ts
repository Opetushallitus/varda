export interface VardaExcelReportDTO {
  id: number;
  filename: string;
  language: string;
  report_type: string;
  report_subtype?: string;
  target_date?: string;
  target_date_secondary?: string;
  status: string;
  organisaatio?: string;
  organisaatio_oid?: string;
  toimipaikka?: string;
  toimipaikka_oid?: string;
  toimipaikka_nimi?: string;
  url?: string;
  timestamp: string;
  user: number;
  password: string;
}

export interface VardaExcelReportPostDTO {
  report_type: string;
  report_subtype?: string;
  language: string;
  organisaatio_oid?: string;
  toimipaikka_oid?: string;
  target_date?: string;
  target_date_secondary?: string;
}
