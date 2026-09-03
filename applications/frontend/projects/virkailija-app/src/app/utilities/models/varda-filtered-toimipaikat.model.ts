import { VardaToimipaikkaMinimalDto } from './dto/varda-toimipaikka-dto.model';

export interface FilteredToimipaikat {
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  katselijaToimipaikat: Array<VardaToimipaikkaMinimalDto>;
  tallentajaToimipaikat: Array<VardaToimipaikkaMinimalDto>;
}
