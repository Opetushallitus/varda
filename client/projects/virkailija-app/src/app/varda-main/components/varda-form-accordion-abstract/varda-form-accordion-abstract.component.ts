import { Component, Output, ViewChild, EventEmitter, Input, OnInit, OnDestroy } from '@angular/core';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { PuutteellinenErrorDTO } from '../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { MatExpansionPanel, MatExpansionPanelHeader } from '@angular/material/expansion';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { FormGroup } from '@angular/forms';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { Subscription } from 'rxjs';

@Component({
  template: ''
})
export abstract class VardaFormAccordionAbstractComponent<T extends {id?: number}> implements OnInit, OnDestroy {
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  @ViewChild('matPanel') matPanel: MatExpansionPanel;
  @Input() currentObject: T;
  @Output() closeEmitter = new EventEmitter();
  @Output() setBaseObject = new EventEmitter<any>();

  i18n = VirkailijaTranslations;
  formGroup: FormGroup;
  isEdit: boolean;
  isSubmitting = false;

  protected errorList: Array<PuutteellinenErrorDTO>;
  protected subscriptions: Array<Subscription> = [];

  constructor(protected modalService: VardaModalService) { }

  ngOnInit() {
    this.initForm();

    if (!this.objectExists()) {
      this.togglePanel(true);
      this.enableForm();
      setTimeout(() => this.panelHeader?.focus(), 200);
    } else {
      this.disableForm();
    }

    if (this.currentObject && !this.currentObject.id) {
      // Object is created from a copy so it can be saved immediately
      this.formGroup.markAsDirty();
    }
  }

  checkFormErrors(apiService: VardaLapsiService | VardaHenkilostoApiService | VardaVakajarjestajaApiService, modelName: string, modelID: number) {
    if (modelID) {
      apiService.getFormErrorList().subscribe(errorList => {
        this.errorList = errorList.filter(error => error.model_name === modelName && error.model_id_list.includes(modelID));
      });
    }
  }

  togglePanel(open: boolean) {
    setTimeout(() => {
      if (open) {
        this.matPanel?.open();
      } else {
        this.matPanel?.close();
      }
    }, 100);

    if (!open) {
      this.disableForm();
      this.closeEmitter?.emit();
      // Reset fields when accordion is closed
      this.initForm();
    }
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
  }

  disableForm() {
    this.isEdit = false;
    this.formGroup.disable();
    this.modalService.setFormValuesChanged(false);
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 500);
  }

  useAsCopy(event: MouseEvent) {
    event.stopPropagation();
    this.setBaseObject.emit(this.currentObject);
  }

  objectExists() {
    return !!this.currentObject?.id;
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  abstract initForm();
}
