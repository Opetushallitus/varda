import { Component, EventEmitter, Input, Output } from '@angular/core';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { PuutteellinenToimipaikkaListDTO } from '../../../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-puutteelliset-list',
  templateUrl: './puutteelliset-list.component.html',
  styleUrls: ['./puutteelliset-list.component.css', '../../../varda-main-frame/varda-henkilo-list/varda-henkilo-list.component.css']
})
export class PuutteellisetListComponent {
  @Output() openErrorForm = new EventEmitter<HenkiloListDTO | PuutteellinenToimipaikkaListDTO>(true);
  @Input() errorList: Array<HenkiloListDTO | PuutteellinenToimipaikkaListDTO>;

  koodistoEnum = KoodistoEnum;

  constructor() { }

  clickErrorItem(instance: HenkiloListDTO | PuutteellinenToimipaikkaListDTO) {
    this.openErrorForm.emit(instance);
  }
}
