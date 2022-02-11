export class VardaYearlyReportDTO {
  id: number;
  vakajarjestaja?: string;
  status: string;
  tilasto_pvm: string;
  poiminta_pvm?: string;
  vakajarjestaja_count?: number;
  vakajarjestaja_is_active?: boolean;
  toimipaikka_count?: number;
  toimintapainotus_count?: number;
  kielipainotus_count?: number;
  yhteensa_henkilo_count?: number;
  yhteensa_lapsi_count?: number;
  yhteensa_varhaiskasvatussuhde_count?: number;
  yhteensa_varhaiskasvatuspaatos_count?: number;
  yhteensa_vuorohoito_count?: number;
  oma_henkilo_count?: number;
  oma_lapsi_count?: number;
  oma_varhaiskasvatussuhde_count?: number;
  oma_varhaiskasvatuspaatos_count?: number;
  oma_vuorohoito_count?: number;
  paos_henkilo_count?: number;
  paos_lapsi_count?: number;
  paos_varhaiskasvatussuhde_count?: number;
  paos_varhaiskasvatuspaatos_count?: number;
  paos_vuorohoito_count?: number;
  yhteensa_maksutieto_count?: number;
  yhteensa_maksutieto_mp01_count?: number;
  yhteensa_maksutieto_mp02_count?: number;
  yhteensa_maksutieto_mp03_count?: number;
  oma_maksutieto_count?: number;
  oma_maksutieto_mp01_count?: number;
  oma_maksutieto_mp02_count?: number;
  oma_maksutieto_mp03_count?: number;
  paos_maksutieto_count?: number;
  paos_maksutieto_mp01_count?: number;
  paos_maksutieto_mp02_count?: number;
  paos_maksutieto_mp03_count?: number;
}

export interface VardaYearlyReportPostDTO {
  vakajarjestaja_input: string;
  tilastovuosi: number;
  poiminta_pvm: string;
}
