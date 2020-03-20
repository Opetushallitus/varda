import { HenkiloDTO } from './henkilo-dto';
import { ToimipaikkaDTO } from './toimipaikka-dto';

export interface HuoltajanLapsiDTO {
  henkilo: HenkiloDTO;
  voimassaolevia_varhaiskasvatuspaatoksia: number;
  toimipaikat?: Array<ToimipaikkaDTO>;
}
