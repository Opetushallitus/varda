import { ToimipaikkaDTO } from './toimipaikka-dto';

export interface VarhaiskasvatussuhdeDTO {
  id: number;
  alkamis_pvm: string;
  paattymis_pvm?: string;
  toimipaikka: ToimipaikkaDTO;
}
