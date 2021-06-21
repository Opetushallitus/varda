import { Component, Output, ViewChild, EventEmitter } from '@angular/core';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { PuutteellinenErrorDTO } from '../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { MatExpansionPanel } from '@angular/material/expansion';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { FormGroup } from '@angular/forms';
import { VardaModalService } from '../../../core/services/varda-modal.service';

@Component({
  selector: 'app-varda-form-accordion-abstract',
  template: ''
})
export class VardaFormAccordionAbstractComponent {
  @ViewChild('matPanel') matPanel: MatExpansionPanel;
  @Output() closeEmitter = new EventEmitter<boolean>(true);

  i18n = VirkailijaTranslations;
  formGroup: FormGroup;
  isEdit: boolean;

  protected errorList: Array<PuutteellinenErrorDTO>;

  constructor(protected modalService: VardaModalService) { }

  checkFormErrors(apiService: VardaLapsiService | VardaHenkilostoApiService | VardaVakajarjestajaApiService, modelName: string, modelID: number) {
    if (modelID) {
      apiService.getFormErrorList().subscribe(errorList => {
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
