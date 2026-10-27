import { VarhaiskasvatuspaatosDTO } from './varhaiskasvatuspaatos-dto';

export interface VarhaiskasvatustiedotDTO {
  lapset: Array<LapsiDTO>;
  voimassaolevia_varhaiskasvatuspaatoksia: number;
}

export interface LapsiDTO {
  id: number;
  aktiivinen_toimija?: boolean;
  yhteysosoite?: string;
  varhaiskasvatuksen_jarjestaja?: string;
  varhaiskasvatuspaatokset?: Array<VarhaiskasvatuspaatosDTO>;
  varhaiskasvatuspaatos?: VarhaiskasvatuspaatosDTO;
}
