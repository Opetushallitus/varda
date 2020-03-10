import { VardaToimipaikkaMinimalDto } from "./dto/varda-toimipaikka-dto.model";

export interface VakajarjestajaToimipaikat {
  allToimipaikat: Array<VardaToimipaikkaMinimalDto>,
  toimipaikat: Array<VardaToimipaikkaMinimalDto>,
  katselijaToimipaikat: Array<VardaToimipaikkaMinimalDto>,
  tallentajaToimipaikat: Array<VardaToimipaikkaMinimalDto>
}
