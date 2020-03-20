import { VarhaiskasvatuspaatosDTO } from './varhaiskasvatuspaatos-dto';

export interface VarhaiskasvatussuhdeDTO {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm?: string;
  varhaiskasvatuspaatos?: VarhaiskasvatuspaatosDTO;
}
