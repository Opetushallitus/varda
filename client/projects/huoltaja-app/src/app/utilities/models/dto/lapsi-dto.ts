import { VarhaiskasvatuspaatosDTO } from './varhaiskasvatuspaatos-dto';

export interface LapsiDTO {
  id: number;
  yhteysosoite?: string;
  varhaiskasvatuksen_jarjestaja?: string;
  varhaiskasvatuspaatokset?: Array<VarhaiskasvatuspaatosDTO>;
  varhaiskasvatuspaatos?: VarhaiskasvatuspaatosDTO;
}
