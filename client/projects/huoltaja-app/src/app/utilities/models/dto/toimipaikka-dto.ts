import { VarhaiskasvatussuhdeDTO } from './varhaiskasvatussuhde-dto';

export interface ToimipaikkaDTO {
  toimipaikka_nimi: string;
  toimipaikka_kunta_koodi: string;
  varhaiskasvatussuhteet: Array<VarhaiskasvatussuhdeDTO>;
}
