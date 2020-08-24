import { VardaLapsiDTO } from './dto/varda-lapsi-dto.model';
import { VardaHenkiloDTO } from './dto/varda-henkilo-dto.model';
import { HenkiloRooliEnum } from './enums/henkilorooli.enum';
export class VardaExtendedHenkiloModel {
  henkilo?: VardaHenkiloDTO;
  lapsi?: VardaLapsiDTO;
  tyontekija?: any;
  isNew?: boolean;
  hasVarhaiskasvatussuhde?: boolean;
  hasEsiopetussuhde?: boolean;
  rooli?: HenkiloRooliEnum;
}

