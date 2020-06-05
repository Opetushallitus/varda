import { HenkiloDTO } from './henkilo-dto';
import { LapsiDTO } from './lapsi-dto';

export interface HuoltajanLapsiDTO {
  henkilo: HenkiloDTO;
  voimassaolevia_varhaiskasvatuspaatoksia?: number;
  lapset?: Array<LapsiDTO>;
}
