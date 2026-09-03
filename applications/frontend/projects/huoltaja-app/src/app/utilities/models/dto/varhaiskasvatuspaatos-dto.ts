import { VarhaiskasvatussuhdeDTO } from './varhaiskasvatussuhde-dto';

export interface VarhaiskasvatuspaatosDTO {
  id: number;
  alkamis_pvm: string;
  hakemus_pvm: string;
  paattymis_pvm?: string;
  tilapainen_vaka_kytkin?: boolean;
  paivittainen_vaka_kytkin?: boolean;
  kokopaivainen_vaka_kytkin?: boolean;
  jarjestamismuoto_koodi: string;
  vuorohoito_kytkin: boolean;
  pikakasittely_kytkin: boolean;
  tuntimaara_viikossa: number;
  varhaiskasvatussuhteet: Array<VarhaiskasvatussuhdeDTO>;
  toggle_expanded?: boolean;

}
