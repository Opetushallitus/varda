import { Component, Input } from '@angular/core';
import {ToimipaikanLapsiMaksutieto} from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { KoodistoEnum, VardaKoodistoService } from 'varda-shared';

@Component({
  selector: 'app-toimipaikan-lapset-maksutiedot',
  templateUrl: './toimipaikan-lapset-maksutiedot.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetMaksutiedotComponent {
  @Input() maksutieto: ToimipaikanLapsiMaksutieto;
  @Input() isYksityinen: boolean;

  koodistoEnum = KoodistoEnum;

  constructor(private koodistoService: VardaKoodistoService) {}

  getCodeFromKoodistoService(koodistoName: KoodistoEnum, code: string) {
    return this.koodistoService.getCodeValueFromKoodisto(koodistoName, code);
  }
}
