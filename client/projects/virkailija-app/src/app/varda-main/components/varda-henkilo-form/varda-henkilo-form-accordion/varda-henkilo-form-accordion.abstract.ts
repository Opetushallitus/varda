import { Component, EventEmitter, Output, ViewChild } from '@angular/core';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { HenkiloListErrorDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { MatExpansionPanel } from '@angular/material/expansion';
import { FormGroup } from '@angular/forms';
import { VardaModalService } from '../../../../core/services/varda-modal.service';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-varda-henkilo-form-accordion',
  template: ''
})
export class VardaHenkiloFormAccordionAbstractComponent {
  @ViewChild('matPanel') matPanel: MatExpansionPanel;
  @Output() closeEmitter = new EventEmitter<boolean>(true);

  protected errorList: Array<HenkiloListErrorDTO>;

  i18n = VirkailijaTranslations;
  formGroup: FormGroup;
  isEdit: boolean;

  constructor(protected modalService: VardaModalService) { }

  checkFormErrors(henkiloService: VardaLapsiService | VardaHenkilostoApiService, modelName: string, modelID: number) {
    if (modelID) {
      henkiloService.getFormErrorList().subscribe(errorList => {
        this.errorList = errorList.filter(error => error.model_name === modelName && error.model_id_list.includes(modelID));
      });
    }
  }

  togglePanel(open: boolean, refreshList?: boolean, forceState?: boolean) {
    if (forceState) {
      setTimeout(() => {
        if (open) {
          this.matPanel?.open();
        } else {
          this.matPanel?.close();
        }
      }, 100);
    }

    if (!open || refreshList) {
      this.disableForm();
      this.closeEmitter?.emit(refreshList);
      if (refreshList) {
        this.sendUpdateList();
      }
    }
  }

  disableForm() {
    this.isEdit = false;
    this.formGroup.disable();
    this.modalService.setFormValuesChanged(false);
  }

  sendUpdateList() { }
}
