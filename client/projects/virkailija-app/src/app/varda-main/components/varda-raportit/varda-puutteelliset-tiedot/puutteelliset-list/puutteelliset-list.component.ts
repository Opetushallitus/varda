import { Component, EventEmitter, Input, Output } from '@angular/core';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { PuutteellinenToimipaikkaListDTO } from '../../../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { KoodistoEnum } from 'varda-shared';
import { VardaUtilityService } from '../../../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../../../utilities/models/enums/model-name.enum';

@Component({
  selector: 'app-puutteelliset-list',
  templateUrl: './puutteelliset-list.component.html',
  styleUrls: ['./puutteelliset-list.component.css', '../../../varda-main-frame/varda-henkilo-list/varda-henkilo-list.component.css']
})
export class PuutteellisetListComponent {
  @Output() openErrorForm = new EventEmitter<HenkiloListDTO | PuutteellinenToimipaikkaListDTO>(true);
  @Input() errorList: Array<HenkiloListDTO | PuutteellinenToimipaikkaListDTO>;

  koodistoEnum = KoodistoEnum;

  constructor(private utilityService: VardaUtilityService) { }

  clickErrorItem(instance: HenkiloListDTO | PuutteellinenToimipaikkaListDTO) {
    this.openErrorForm.emit(instance);
    // Set focus on the first error
    const error = instance.errors[0];
    if (Object.values(ModelNameEnum).map(value => value as string).includes(error.model_name)) {
      this.utilityService.setFocusObjectSubject({type: error.model_name as ModelNameEnum, id: error.model_id_list[0]});
    }
  }
}
