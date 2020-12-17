import { Component } from '@angular/core';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { HenkiloListErrorDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';

@Component({
  selector: 'app-varda-henkilo-form-accordion',
  template: ''
})
export class VardaHenkiloFormAccordionAbstractComponent {
  protected errorList: Array<HenkiloListErrorDTO>;


  constructor() { }

  checkFormErrors(henkiloService: VardaLapsiService | VardaHenkilostoApiService, modelName: string, modelID: number) {
    if (modelID) {
      henkiloService.getFormErrorList().subscribe(errorList => {
        this.errorList = errorList.filter(error => error.model_name === modelName && error.model_id_list.includes(modelID));
      });
    }
  }
}
