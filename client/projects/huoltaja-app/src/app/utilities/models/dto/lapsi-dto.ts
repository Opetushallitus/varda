import { VarhaiskasvatuspaatosDTO } from './varhaiskasvatuspaatos-dto';

export interface LapsiDTO {
  id: number;
  oma_organisaatio_sahkoposti?: string;
  varhaiskasvatuspaatokset: VarhaiskasvatuspaatosDTO;
}
