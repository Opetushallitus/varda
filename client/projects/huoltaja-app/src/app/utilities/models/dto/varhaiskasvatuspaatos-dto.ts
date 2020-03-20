export interface VarhaiskasvatuspaatosDTO {
  id: number;
  alkamis_pvm: string;
  hakemus_pvm: string;
  paattymis_pvm?: string;
  paivittainen_vaka_kytkin?: boolean;
  osaviikkoinen_vaka_kytkin: boolean;
  kokopaivainen_vaka_kytkin?: boolean;
  osa_aikainen_vaka_kytkin: boolean;
  jarjestamismuoto_koodi: string;
  vuorohoito_kytkin: boolean;
  pikakasittely_kytkin: boolean;
  tuntimaara_viikossa: number;
  toggle_expanded?: boolean;
}
