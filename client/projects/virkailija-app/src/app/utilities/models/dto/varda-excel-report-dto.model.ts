export interface VardaExcelReportDTO {
  id: number;
  filename: string;
  language: string;
  report_type: string;
  target_date?: string;
  target_date_start?: string;
  target_date_end?: string;
  status: string;
  vakajarjestaja: string;
  vakajarjestaja_oid: string;
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
  language: string;
  vakajarjestaja_oid: string;
  toimipaikka_oid?: string;
  target_date?: string;
  target_date_start?: string;
  target_date_end?: string;
}
