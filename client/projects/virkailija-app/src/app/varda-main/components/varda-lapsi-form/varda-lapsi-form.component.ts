import {
  AfterViewInit,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild,
  ViewChildren
} from '@angular/core';
import { FormArray, FormControl, FormGroup } from '@angular/forms';
import { MatStepper } from '@angular/material/stepper';
import {
  VardaEntityNames,
  VardaFieldSet,
  VardaHenkiloDTO,
  VardaKayttooikeusRoles,
  VardaLapsiDTO,
  VardaToimipaikkaDTO,
  VardaVakajarjestajaUi,
  VardaVarhaiskasvatuspaatosDTO,
  VardaVarhaiskasvatussuhdeDTO
} from '../../../utilities/models';
import { VardaFormService } from '../../../core/services/varda-form.service';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { VardaValidatorService } from '../../../core/services/varda-validator.service';
import { VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { forkJoin, Observable, Subscription } from 'rxjs';
import { VardaDateService } from '../../services/varda-date.service';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { PaosToimintatietoDto } from '../../../utilities/models/dto/varda-paos-dto';
import { UserAccess, SaveAccess } from '../../../utilities/models/varda-user-access.model';

declare var $: any;

@Component({
  selector: 'app-varda-lapsi-form',
  templateUrl: './varda-lapsi-form.component.html',
  styleUrls: ['./varda-lapsi-form.component.css']
})
export class VardaLapsiFormComponent implements OnInit, OnChanges, AfterViewInit {
  @Input() henkilo: VardaHenkiloDTO;
  @Input() isEdit: boolean;
  @Input() toimipaikka: VardaToimipaikkaDTO;
  @Output() saveLapsiSuccess: EventEmitter<any> = new EventEmitter();
  @Output() saveLapsiFailure: EventEmitter<any> = new EventEmitter();
  @Output() updateLapsi: EventEmitter<any> = new EventEmitter();
  @Output() deleteLapsi: EventEmitter<any> = new EventEmitter();
  @Output() valuesChanged: EventEmitter<any> = new EventEmitter();
  @ViewChild('lapsiStepper') lapsiStepper: MatStepper;
  @ViewChildren('varhaiskasvatuspaatosPanels') varhaiskasvatuspaatosPanels: any;
  @ViewChildren('varhaiskasvatussuhdePanels') varhaiskasvatussuhdePanels: any;

  currentLapsi: VardaLapsiDTO;
  currentToimipaikka: VardaToimipaikkaDTO;

  lapsiForm: FormGroup;
  toimipaikkaForm: FormGroup;
  selectedSuhdeForm: FormGroup;
  varhaiskasvatussuhdeForm: FormGroup;
  varhaiskasvatuspaatosForm: FormGroup;
  addVarhaiskasvatussuhde = false;

  varhaiskasvatussuhteetForm: FormGroup; // Combine or separate with "varhaiskasvatussuhdeForm"
  varhaiskasvatussuhteetFieldSets: { [key: string]: Array<VardaFieldSet> };
  varhaiskasvatussuhteetFieldSetsTemplate: Array<VardaFieldSet>;

  varhaiskasvatuspaatoksetForm: FormGroup;
  varhaiskasvatuspaatoksetFieldSets: { [key: string]: Array<VardaFieldSet> };
  varhaiskasvatuspaatoksetFieldSetsTemplate: Array<VardaFieldSet>;

  toimipaikkaOptions: Array<VardaToimipaikkaDTO>;
  varhaiskasvatussuhteet: Array<VardaVarhaiskasvatussuhdeDTO>;
  varhaiskasvatuspaatokset: Array<VardaVarhaiskasvatuspaatosDTO>;

  selectedToimipaikka: VardaToimipaikkaDTO;

  lapsiFormErrors: Array<any>;

  varhaiskasvatuspaatoksetFormChanged: boolean;
  varhaiskasvatussuhteetFormChanged: boolean;

  selectedVakajarjestaja: VardaVakajarjestajaUi & PaosToimintatietoDto;
  selectedVakajarjestajaGlobal: VardaVakajarjestajaUi;
  vakajarjestajat: Array<PaosToimintatietoDto>;
  toimipaikkaAccess: UserAccess;

  ui: {
    noVarhaiskasvatustietoPrivileges: boolean;
    isPerustiedotLoading: boolean,
    isSubmitting: boolean,
    saveBtnText: string,
    lapsiFormSaveSuccess: boolean,
    lapsiFormHasErrors: boolean,
    formSaveSuccessMsg: string,
    formSaveFailureMsg: string,
    selectedVarhaiskasvatuspaatosIndexToDelete: number,
    selectedVarhaiskasvatussuhdeIndexToDelete: number,
    showVarhaiskasvatuspaatosAllDeleteWarning: boolean,
    showVarhaiskasvatussuhdeAllDeleteWarning: boolean,
    openedVarhaiskasvatuspaatosIndex: number,
    openedVarhaiskasvatussuhdeIndex: number,
    showErrorMessageInfo: boolean,
    errorMessageInfo: string,
    kunnanJarjestamaVarhaiskasvatus: boolean
  };

  constructor(
    private vardaFormService: VardaFormService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaUtilityService: VardaUtilityService,
    private vardaValidatorService: VardaValidatorService,
    private vardaErrorMessageService: VardaErrorMessageService,
    private vardaDateService: VardaDateService,
    private translateService: TranslateService,
    private authService: AuthService) {
    this.ui = {
      noVarhaiskasvatustietoPrivileges: true,
      isPerustiedotLoading: false,
      isSubmitting: false,
      saveBtnText: '',
      lapsiFormSaveSuccess: false,
      lapsiFormHasErrors: false,
      formSaveSuccessMsg: '',
      formSaveFailureMsg: '',
      selectedVarhaiskasvatuspaatosIndexToDelete: null,
      selectedVarhaiskasvatussuhdeIndexToDelete: null,
      showVarhaiskasvatuspaatosAllDeleteWarning: false,
      showVarhaiskasvatussuhdeAllDeleteWarning: false,
      openedVarhaiskasvatuspaatosIndex: null,
      openedVarhaiskasvatussuhdeIndex: null,
      showErrorMessageInfo: false,
      errorMessageInfo: '',
      kunnanJarjestamaVarhaiskasvatus: false
    };

    this.vardaApiWrapperService.getPaosJarjestajat(this.vardaVakajarjestajaService.selectedVakajarjestaja.id).subscribe((data) => {
      this.vakajarjestajat = data;
    });
    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
    this.selectedVakajarjestajaGlobal = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
  }

  addNewRecurringStructure(entityName: string): void {
    let formArr: FormArray;
    let fieldSets: any;
    let fieldSetCopy: Array<VardaFieldSet>;
    let panelToOpen, panels;

    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      formArr = <FormArray>this.varhaiskasvatuspaatoksetForm.get('varhaiskasvatuspaatoksetFormArr');
      fieldSetCopy = this.vardaUtilityService.deepcopyArray(this.varhaiskasvatuspaatoksetFieldSetsTemplate);
      fieldSets = this.varhaiskasvatuspaatoksetFieldSets;
      this.ui.openedVarhaiskasvatuspaatosIndex = formArr.length;
      panels = this.varhaiskasvatuspaatosPanels;
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      formArr = <FormArray>this.varhaiskasvatussuhteetForm.get('varhaiskasvatussuhteetFormArr');
      fieldSetCopy = this.vardaUtilityService.deepcopyArray(this.varhaiskasvatussuhteetFieldSetsTemplate);
      fieldSets = this.varhaiskasvatussuhteetFieldSets;
      this.ui.openedVarhaiskasvatussuhdeIndex = formArr.length;
      panels = this.varhaiskasvatussuhdePanels;
    }

    const fg = this.vardaFormService.initFieldSetFormGroup(fieldSetCopy, null);
    if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      fg.addControl('varhaiskasvatuspaatos', new FormControl(this.varhaiskasvatuspaatokset[0]));
      fg.addControl('toimipaikka', new FormControl(this.currentToimipaikka));
    }

    formArr.push(fg);
    fieldSets[formArr.length - 1] = fieldSetCopy;

    setTimeout(() => {
      panels = panels.toArray();
      panelToOpen = panels[formArr.length - 1];
      if (panelToOpen) {
        panelToOpen.open();
      }
    });

    setTimeout(() => {
      this.setRecurringStructureFocus(entityName);
    }, 500);

  }

  cancelDelete(entity: string): void {
    if (entity === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      this.ui.selectedVarhaiskasvatuspaatosIndexToDelete = null;
    } else if (entity === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      this.ui.selectedVarhaiskasvatussuhdeIndexToDelete = null;
    }
  }

  displayDeleteWarning(entityName: string, formArrIndex: number): void {
    let entityToDelete;
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      entityToDelete = this.varhaiskasvatuspaatokset[formArrIndex];
      this.ui.selectedVarhaiskasvatuspaatosIndexToDelete = formArrIndex;
      setTimeout(() => $(`#varhaiskasvatuspaatosCancelDeleteBtn${formArrIndex}`).focus());
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      entityToDelete = this.varhaiskasvatussuhteet[formArrIndex];
      this.ui.selectedVarhaiskasvatussuhdeIndexToDelete = formArrIndex;
      setTimeout(() => $(`#varhaiskasvatussuhdeCancelDeleteBtn${formArrIndex}`).focus());
    }

    if (!entityToDelete) {
      this.ui.selectedVarhaiskasvatuspaatosIndexToDelete = null;
      this.ui.selectedVarhaiskasvatussuhdeIndexToDelete = null;
      this.confirmDeleteAction(entityName, formArrIndex, false);
      return;
    }
  }

  getFieldsetTitle(fieldSet: VardaFieldSet): string {
    let rv;
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'titleSv' : 'titleFi';
    if (fieldSet.title && fieldSet.title[prop]) {
      rv = fieldSet.title[prop];
    }
    return rv;
  }

  getDeleteButtonStyles(entityName: string, index: number): string {
    let rv = '';
    let entity;
    if (this.ui.isSubmitting) {
      rv += 'varda-disabled-button';
    }

    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      entity = this.varhaiskasvatuspaatokset[index];
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      entity = this.varhaiskasvatussuhteet[index];
    }

    if (entity) {
      rv += ' varda-button-danger';
    } else {
      rv += ' varda-button-neutral';
    }

    return rv;
  }

  getDeleteText(entity: string, formArrIndex: number): string {
    let entityToDelete;
    if (entity === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      entityToDelete = this.varhaiskasvatuspaatokset[formArrIndex];
    } else if (entity === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      entityToDelete = this.varhaiskasvatussuhteet[formArrIndex];
    }

    if (!entityToDelete) {
      return 'label.cancel';
    } else {
      return 'label.delete';
    }
  }

  confirmDeleteAction(entity: string, formArrIndex: number, showMsg: boolean): void {
    let entityToDelete, formArr, entities, successMsg;
    if (entity === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      entityToDelete = this.varhaiskasvatuspaatokset[formArrIndex];
      formArr = <FormArray>this.varhaiskasvatuspaatoksetForm.get('varhaiskasvatuspaatoksetFormArr');
      entities = this.varhaiskasvatuspaatokset;
      successMsg = 'alert.delete-varhaiskasvatuspaatos-success';
      this.ui.selectedVarhaiskasvatuspaatosIndexToDelete = formArrIndex;
    } else if (entity === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      entityToDelete = this.varhaiskasvatussuhteet[formArrIndex];
      formArr = <FormArray>this.varhaiskasvatussuhteetForm.get('varhaiskasvatussuhteetFormArr');
      entities = this.varhaiskasvatussuhteet;
      successMsg = 'alert.delete-varhaiskasvatussuhde-success';
      this.ui.selectedVarhaiskasvatussuhdeIndexToDelete = formArrIndex;
    }

    if (entityToDelete) {
      this.ui.lapsiFormHasErrors = false;
      const entityObjId = this.vardaUtilityService.parseIdFromUrl(entityToDelete.url);
      this.getDeleteEndpointByEntityName(entity, entityObjId).subscribe(() => {
        const indexToRemove = entities.findIndex((item) => item.url === entityToDelete.url);
        entities.splice(indexToRemove, 1);
        formArr.removeAt(formArrIndex);

        if (entity === VardaEntityNames.VARHAISKASVATUSPAATOS &&
          formArr.length === 0) {
          this.deleteLapsiRole(entityToDelete.lapsi);
        } else {
          this.ui.lapsiFormSaveSuccess = true;
        }
      }, this.onSaveError.bind(this, formArrIndex, entity));
    } else {
      formArr.removeAt(formArrIndex);
    }

    this.ui.selectedVarhaiskasvatuspaatosIndexToDelete = null;
    this.ui.selectedVarhaiskasvatussuhdeIndexToDelete = null;
    if (showMsg) {
      this.ui.formSaveSuccessMsg = successMsg;
      this.hideMessages();
    }
  }

  deleteLapsiRole(lapsiReference: string): void {
    const lapsiId = this.vardaUtilityService.parseIdFromUrl(lapsiReference);
    this.vardaApiWrapperService.deleteLapsi(lapsiId).subscribe(() => {
      this.ui.lapsiFormSaveSuccess = true;
      setTimeout(() => {
        $('#henkiloModal').modal('hide');
        this.deleteLapsi.emit(lapsiReference);
      }, 2000);
    });
  }

  getDeleteEndpointByEntityName(entity: string, id: string): Observable<any> {
    let obs;
    if (entity === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      obs = this.vardaApiWrapperService.deleteVarhaiskasvatuspaatos(id);
    } else if (entity === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      obs = this.vardaApiWrapperService.deleteVarhaiskasvatussuhde(id);
    }
    return obs;
  }

  getRecurringEntityFromDate(index: number, entityStr: string): string {
    const entity = this.getExistingEntityByIndex(index, entityStr);
    let rv = '';
    if (entity) {
      rv = this.vardaDateService.vardaDateToUIStrDate(entity.alkamis_pvm);
    }
    return rv;
  }

  getRecurringEntityHeader(index: number, entityStr: string): string {
    const entity = this.getExistingEntityByIndex(index, entityStr);
    let rv = '';
    if (entity) {
      rv = this.vardaDateService.vardaDateToUIStrDate(entity.alkamis_pvm);
      let tsKey = (entityStr === VardaEntityNames.VARHAISKASVATUSPAATOS) ? 'varhaiskasvatuspaatos.from' : 'varhaiskasvatussuhde.from';
      const translationsParams = {
        value: this.vardaDateService.vardaDateToUIStrDate(entity.alkamis_pvm),
      };

      if (entity.paattymis_pvm) {
        tsKey = (entityStr === VardaEntityNames.VARHAISKASVATUSPAATOS) ? 'varhaiskasvatuspaatos.from-to' : 'varhaiskasvatussuhde.from-to';
        translationsParams['value2'] = this.vardaDateService.vardaDateToUIStrDate(entity.paattymis_pvm);
      }

      this.translateService.get(tsKey, translationsParams).subscribe((st) => rv = st);
    }
    return rv;
  }

  getFormDataByEntityName(index: number, entityName: string): any {
    let rv: any;
    let fieldSets: Array<VardaFieldSet>;
    let fg: FormGroup;
    const data = { formData: {}, fieldSets: {} };
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      const varhaiskasvatuspaatoksetFormArr = <FormArray>this.varhaiskasvatuspaatoksetForm.get('varhaiskasvatuspaatoksetFormArr');
      fg = <FormGroup>varhaiskasvatuspaatoksetFormArr.at(index);
      fieldSets = this.varhaiskasvatuspaatoksetFieldSets[index];
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      const varhaiskasvatussuhteetFormArr = <FormArray>this.varhaiskasvatussuhteetForm.get('varhaiskasvatussuhteetFormArr');
      fg = <FormGroup>varhaiskasvatussuhteetFormArr.at(index);
      fieldSets = this.varhaiskasvatussuhteetFieldSets[index];
    }

    data.formData = Object.assign({}, fg.getRawValue());
    data.fieldSets = fieldSets;
    rv = data;

    return rv;
  }

  getExistingEntityByIndex(index: number, entityName: string): any {
    let entity;
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      entity = this.varhaiskasvatuspaatokset[index];
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      entity = this.varhaiskasvatussuhteet[index];
    }
    return entity;
  }

  hideMessages(): void {
    setTimeout(() => {
      this.ui.lapsiFormSaveSuccess = false;
    }, 3500);
  }

  byEndpoint(item1: any, item2: any): boolean {
    if (!item1 || !item2) {
      return false;
    }
    return item1.url === item2.url;
  }

  getLapsiFormData(): any {

    const data = {
      selectedVakajarjestaja: this.ui.kunnanJarjestamaVarhaiskasvatus
        ? VardaApiService.getVakajarjestajaUrlFromId(this.selectedVakajarjestaja.id || this.selectedVakajarjestaja.vakajarjestaja_id)
        : null,
      lapsi: { formData: {}, fieldSets: {} },
      toimipaikka: { formData: {}, fieldSets: {} },
      varhaiskasvatuspaatos: { formData: {}, fieldSets: {} }
    };

    let varhaiskasvatussuhdeFormData, varhaiskasvatuspaatosFormData;

    if (this.addVarhaiskasvatussuhde) {
      data['varhaiskasvatussuhde'] = { formData: {}, fieldSets: {} };
      varhaiskasvatussuhdeFormData = this.varhaiskasvatussuhdeForm.value;
      varhaiskasvatuspaatosFormData = this.varhaiskasvatuspaatosForm.value;
      data['varhaiskasvatussuhde'].formData = varhaiskasvatussuhdeFormData;
      data['varhaiskasvatussuhde'].fieldSets = this.varhaiskasvatussuhteetFieldSets[0];
      data['varhaiskasvatuspaatos'].formData = varhaiskasvatuspaatosFormData;
      data['varhaiskasvatuspaatos'].fieldSets = this.varhaiskasvatuspaatoksetFieldSets[0];
    }

    data.toimipaikka.formData = this.toimipaikkaForm.value;

    return data;
  }

  initLapsiFormFields(): void {
    this.vardaApiWrapperService.getCreateLapsiFieldSets().subscribe((data) => {
      if (this.toimipaikkaAccess.lapsitiedot.tallentaja) {
        this.toimipaikkaOptions = this.authService.getAuthorizedToimipaikat(this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().tallentajaToimipaikat, SaveAccess.lapsitiedot);
      } else {
        this.toimipaikkaOptions = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().allToimipaikat;
      }
      this.toimipaikkaForm = new FormGroup({ toimipaikka: new FormControl(this.currentToimipaikka) });
      this.selectedSuhdeForm = new FormGroup({ addVarhaiskasvatussuhde: new FormControl() });
      this.setToimipaikka();

      this.varhaiskasvatussuhteetFieldSetsTemplate = data[0].fieldsets;
      this.varhaiskasvatussuhteetFieldSets = {};
      this.varhaiskasvatussuhteetFieldSets[0] = this.vardaUtilityService.deepcopyArray(data[0].fieldsets);
      this.varhaiskasvatussuhdeForm = this.vardaFormService.initFieldSetFormGroup(this.varhaiskasvatussuhteetFieldSetsTemplate, null);
      this.varhaiskasvatussuhteetForm = new FormGroup({});
      const varhaiskasvatussuhteetFormArr = new FormArray([]);

      this.varhaiskasvatuspaatoksetFieldSetsTemplate = data[1].fieldsets;
      this.varhaiskasvatuspaatoksetFieldSets = {};
      this.varhaiskasvatuspaatoksetFieldSets[0] = this.vardaUtilityService.deepcopyArray(data[1].fieldsets);
      this.varhaiskasvatuspaatosForm = this.vardaFormService.initFieldSetFormGroup(this.varhaiskasvatuspaatoksetFieldSetsTemplate, null);
      this.varhaiskasvatuspaatoksetForm = new FormGroup({});
      const varhaiskasvatuspaatoksetFormArr = new FormArray([]);

      if (this.varhaiskasvatussuhteet.length > 0) {
        this.varhaiskasvatussuhteet.forEach((varhaiskasvatussuhdeItem, index) => {
          const copyFieldSet = this.vardaUtilityService.deepcopyArray(this.varhaiskasvatussuhteetFieldSetsTemplate);
          this.varhaiskasvatussuhteetFieldSets[index] = copyFieldSet;
          const varhaiskasvatussuhdeFg = this.vardaFormService.initFieldSetFormGroup(this.varhaiskasvatussuhteetFieldSets[index],
            varhaiskasvatussuhdeItem);
          const selectedToimipaikka = this.getToimipaikkaByUrl(varhaiskasvatussuhdeItem);
          const selectedVarhaiskasvatuspaatos = this.getVarhaiskasvatuspaatosByUrl(varhaiskasvatussuhdeItem);
          const toimipaikkaFc = new FormControl(selectedToimipaikka);
          const varhaiskasvatuspaatosFc = new FormControl(selectedVarhaiskasvatuspaatos);
          toimipaikkaFc.disable();
          varhaiskasvatuspaatosFc.disable();
          varhaiskasvatussuhdeFg.addControl('toimipaikka', toimipaikkaFc);
          varhaiskasvatussuhdeFg.addControl('varhaiskasvatuspaatos', varhaiskasvatuspaatosFc);
          varhaiskasvatussuhteetFormArr.push(varhaiskasvatussuhdeFg);
          this.vardaValidatorService.initFieldStates(copyFieldSet, varhaiskasvatussuhdeFg);
        });
      }

      if (this.varhaiskasvatuspaatokset.length > 0) {
        this.varhaiskasvatuspaatokset.forEach((varhaiskasvatuspaatosItem, index) => {
          const copyFieldSet = this.vardaUtilityService.deepcopyArray(this.varhaiskasvatuspaatoksetFieldSetsTemplate);
          this.varhaiskasvatuspaatoksetFieldSets[index] = copyFieldSet;
          const arr = this.vardaFormService.initFieldSetFormGroup(this.varhaiskasvatuspaatoksetFieldSets[index],
            varhaiskasvatuspaatosItem);
          varhaiskasvatuspaatoksetFormArr.push(arr);
          this.vardaValidatorService.initFieldStates(copyFieldSet, arr);
        });
      }

      this.varhaiskasvatussuhteetForm.addControl('varhaiskasvatussuhteetFormArr', varhaiskasvatussuhteetFormArr);
      this.varhaiskasvatuspaatoksetForm.addControl('varhaiskasvatuspaatoksetFormArr', varhaiskasvatuspaatoksetFormArr);

      this.varhaiskasvatuspaatoksetForm.valueChanges.subscribe(() => {
        if (this.varhaiskasvatuspaatoksetForm.dirty) {
          this.varhaiskasvatuspaatoksetFormChanged = true;
          this.checkIfAnyOfTheFormsHasChanged();
        }
      });

      this.varhaiskasvatussuhteetForm.valueChanges.subscribe(() => {
        if (this.varhaiskasvatussuhteetForm.dirty) {
          this.varhaiskasvatussuhteetFormChanged = true;
          this.checkIfAnyOfTheFormsHasChanged();
        }
      });

      this.ui.isPerustiedotLoading = false;

      this.bindHideSuccessMsg();
    });
  }

  bindHideSuccessMsg(): void {
    setTimeout(() => {
      $('.varda-button, .varda-form-control, .varda-date, .varda-radio, .varda-mat-checkbox').click(() => {
        this.ui.lapsiFormSaveSuccess = false;
      });
    }, 2000);
  }

  checkIfAnyOfTheFormsHasChanged(): void {
    let rv = false;
    if (this.varhaiskasvatuspaatoksetFormChanged ||
      this.varhaiskasvatussuhteetFormChanged) {
      rv = true;
    }
    this.valuesChanged.emit(rv);
  }

  getToimipaikkaByUrl(suhde: any): VardaToimipaikkaDTO {
    return this.toimipaikkaOptions.find((toimipaikkaObj) => toimipaikkaObj.url === suhde.toimipaikka);
  }

  getVarhaiskasvatuspaatosByUrl(varhaiskasvatussuhde: VardaVarhaiskasvatussuhdeDTO): VardaVarhaiskasvatuspaatosDTO {
    return this.varhaiskasvatuspaatokset
      .find((varhaiskasvatuspaatosObj) => varhaiskasvatuspaatosObj.url === varhaiskasvatussuhde.varhaiskasvatuspaatos);
  }

  initExistingLapsiFormData(lapsiReference: string): Observable<any> {
    return new Observable((observer) => {
      return this.vardaApiWrapperService.getEntityReferenceByEndpoint(lapsiReference).subscribe((lapsi) => {
        this.currentLapsi = lapsi;
        const lapsiId = this.vardaUtilityService.parseIdFromUrl(lapsi.url);
        this.ui.isPerustiedotLoading = false;
        this.vardaApiWrapperService.getVarhaiskasvatussuhteetByLapsi(lapsiId).subscribe((vakasuhteet) => {
          this.vardaApiWrapperService.getVarhaiskasvatuspaatoksetByLapsi(lapsiId)
            .subscribe((vakapaatokset) => {

              this.varhaiskasvatussuhteet = [];
              const tempVarhaiskasvatussuhteet = [...vakasuhteet];

              this.varhaiskasvatuspaatokset = [...vakapaatokset];

              this.varhaiskasvatuspaatokset.sort(this.sortRecurringEntityListsByDates.bind(this));

              tempVarhaiskasvatussuhteet.forEach((vakasuhde) => {
                const vakasuhdeVakaPaatosReference = vakasuhde.varhaiskasvatuspaatos;
                const foundVakapaatos =
                  this.varhaiskasvatuspaatokset
                    .find((varhaiskasvatuspaatosObj) => varhaiskasvatuspaatosObj.url === vakasuhdeVakaPaatosReference);
                if (foundVakapaatos) {
                  this.varhaiskasvatussuhteet.push(vakasuhde);
                }
              });

              this.varhaiskasvatussuhteet.sort(this.sortRecurringEntityListsByDates.bind(this));

              observer.next();
              observer.complete();
            }, (e) => {
              console.error(e);
            });
        },
          (e) => observer.error(e));
      });
    });
  }

  setToimipaikka(): void {
    this.selectedToimipaikka = this.toimipaikkaForm.get('toimipaikka').value;
  }

  saveRecurringStructure(formArrIndex: number, entityName: string): void {
    this.ui.lapsiFormHasErrors = false;
    this.ui.isSubmitting = true;
    const formData = this.getFormDataByEntityName(formArrIndex, entityName);
    let isEdit = false;
    const entityToEdit = this.getExistingEntityByIndex(formArrIndex, entityName);
    let recurringSaveObs: Observable<any>;

    if (entityToEdit) {
      isEdit = true;
    }

    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      recurringSaveObs = this.vardaApiWrapperService.saveVarhaiskasvatuspaatos(
        isEdit,
        this.currentLapsi,
        entityToEdit,
        formData
      );
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      recurringSaveObs = this.vardaApiWrapperService.saveVarhaiskasvatussuhde(
        isEdit,
        this.currentLapsi,
        entityToEdit,
        formData);
    }

    recurringSaveObs.subscribe({
      next: this.onSaveSuccess.bind(this, entityName, formArrIndex, isEdit),
      error: this.onSaveError.bind(this, formArrIndex, entityName),
    });
  }

  sortRecurringEntityListsByDates(a: any, b: any): number {
    const alkamisPvmA = this.vardaDateService.vardaDateToMoment(a.alkamis_pvm);

    const uiDateAlkamisPvmB = this.vardaDateService.vardaDateToMoment(b.alkamis_pvm);

    let aIsBeforeB = this.vardaDateService.date1IsAfterDate2(alkamisPvmA, uiDateAlkamisPvmB);

    if (a.paattymis_pvm || b.paattymis_pvm) {
      if (a.paattymis_pvm && !b.paattymis_pvm) {
        aIsBeforeB = false;
      } else if (!a.paattymis_pvm && b.paattymis_pvm) {
        aIsBeforeB = true;
      } else if (a.paattymis_pvm && b.paattymis_pvm) {
        const paattymisPvmA = this.vardaDateService.vardaDateToMoment(a.paattymis_pvm);

        const paattymisPvmB = this.vardaDateService.vardaDateToMoment(b.paattymis_pvm);

        aIsBeforeB = this.vardaDateService.date1IsAfterDate2(paattymisPvmA, paattymisPvmB);
      }
    }

    if (aIsBeforeB) {
      return -1;
    }

    if (!aIsBeforeB) {
      return 1;
    }

    return 0;
  }

  addLapsiFormValid(): boolean {
    let rv;

    if (this.addVarhaiskasvatussuhde) {
      rv = this.varhaiskasvatussuhdeForm.valid && this.varhaiskasvatuspaatosForm.valid;
    }

    return rv;
  }

  ngAfterViewInit() { }

  // Used for creating lapsi, not edit
  saveLapsi(): void {
    this.ui.isSubmitting = true;
    const formData = this.getLapsiFormData();
    this.vardaApiWrapperService.createNewLapsi(this.henkilo, this.selectedToimipaikka,
      {
        addVarhaiskasvatussuhde: this.addVarhaiskasvatussuhde
      }, formData).subscribe((henkilo) => {
        setTimeout(() => {
          this.ui.isSubmitting = false;
          this.saveLapsiSuccess.emit(henkilo);
        }, 2000);
      }, (e) => {
        this.ui.isSubmitting = false;
        this.saveLapsiFailure.emit(e);
      });
  }

  onFieldChanged(data: any): void {
    const field = data.field,
      formArrIndex = data.formArrIndex,
      formName = data.formName;

    let formArray, fieldSets;

    if (formName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      formArray = this.isEdit ?
        <FormArray>this.varhaiskasvatuspaatoksetForm.get('varhaiskasvatuspaatoksetFormArr') :
        <FormGroup>this.varhaiskasvatuspaatosForm;
      fieldSets = this.isEdit ? this.varhaiskasvatuspaatoksetFieldSets[formArrIndex] : this.varhaiskasvatuspaatoksetFieldSetsTemplate;
    } else if (formName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      formArray = <FormArray>this.varhaiskasvatussuhteetForm.get('varhaiskasvatussuhteetFormArr');
      fieldSets = this.varhaiskasvatussuhteetFieldSets[formArrIndex];
    }


    const formToValidate = this.isEdit ? <FormGroup>formArray.at(formArrIndex) : formArray;
    this.vardaValidatorService.validate(field, fieldSets, formToValidate);
  }

  onSaveSuccess(...args): void {
    setTimeout(() => {
      const action = args[0];
      const formArrIndex = args[1];
      const isEdit = args[2];
      const entity = args[3];

      let currentPanels;
      let entities, formArray;
      if (action === VardaEntityNames.VARHAISKASVATUSPAATOS) {
        currentPanels = this.varhaiskasvatuspaatosPanels.toArray();
        this.updateLapsi.emit({ saveVarhaiskasvatuspaatos: { url: this.currentLapsi.url, entity: entity } });
        entities = this.varhaiskasvatuspaatokset;
        formArray = <FormArray>this.varhaiskasvatuspaatoksetForm.get('varhaiskasvatuspaatoksetFormArr');
      } else if (action === VardaEntityNames.VARHAISKASVATUSSUHDE) {
        currentPanels = this.varhaiskasvatussuhdePanels.toArray();
        entities = this.varhaiskasvatussuhteet;
        formArray = <FormArray>this.varhaiskasvatussuhteetForm.get('varhaiskasvatussuhteetFormArr');
      }

      if (entities) {

        if (isEdit) {
          entities[formArrIndex] = entity;
        } else {
          entities.push(entity);
        }

        entities.sort(this.sortRecurringEntityListsByDates.bind(this));
      }


      this.ui.formSaveSuccessMsg = 'alert.modal-generic-save-success';
      this.ui.lapsiFormSaveSuccess = true;
      currentPanels[formArrIndex].close();

      setTimeout(() => {
        const newIndex = entities.findIndex((r) => {
          return r.url === entity.url;
        });
        const entityToBeMoved = formArray.at(formArrIndex);
        formArray.removeAt(formArrIndex);
        formArray.insert(newIndex, entityToBeMoved);
        setTimeout(() => {
          this.setControlsDisabledOnEdit(action, entityToBeMoved);
          this.setFormsChangedState(action, false);
          this.checkIfAnyOfTheFormsHasChanged();
          this.setRecurringStructureFocus(action, newIndex);
        }, 1000);
      }, 1000);

      this.ui.isSubmitting = false;
    }, 1000);
  }

  selectedSuhdeFieldChange(suhde: string, $event: any): void {
    const checked = $event.checked;
    if (suhde === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      this.addVarhaiskasvatussuhde = checked;
    }
  }

  setControlsDisabledOnEdit(entityName: string, form: FormGroup): void {
    let fieldsetTemplate;
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      fieldsetTemplate = this.varhaiskasvatuspaatoksetFieldSetsTemplate;
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      fieldsetTemplate = this.varhaiskasvatussuhteetFieldSetsTemplate;
    }

    fieldsetTemplate.forEach(fieldSet => {
      fieldSet.fields.forEach(field => {
        if (field && field.rules && field.rules.disabledOnEdit) {
          const fc = this.vardaFormService.findFormControlFromFormGroupByFieldKey(field.key, form);
          fc.disable();
        }
      });
    });
  }

  setFormsChangedState(entityName: string, state: boolean): void {
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      this.varhaiskasvatuspaatoksetFormChanged = state;
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      this.varhaiskasvatussuhteetFormChanged = state;
    }
  }

  setRecurringStructureFocus(entityName: string, index?: number): void {
    let recurringStructureSelectorToFocus;
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      recurringStructureSelectorToFocus = $('.recurring-varhaiskasvatuspaatos-entity-header');
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      recurringStructureSelectorToFocus = $('.recurring-varhaiskasvatussuhde-entity-header');
    }

    if (!isNaN(index)) {
      recurringStructureSelectorToFocus.get(index).focus();
    } else {
      recurringStructureSelectorToFocus.last().focus();
    }
  }

  onSaveError(...args): void {
    this.ui.formSaveFailureMsg = '';
    this.ui.errorMessageInfo = '';
    this.ui.showErrorMessageInfo = false;
    const formArrIndex = args[0];
    const entity = args[1];
    const eObj = args[2];
    let e, translationKey;
    if (entity === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      e = this.varhaiskasvatuspaatokset[formArrIndex];
      translationKey = 'varhaiskasvatuspaatos.from';
    } else if (entity === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      e = this.varhaiskasvatussuhteet[formArrIndex];
      translationKey = 'varhaiskasvatussuhde.from';
    }

    if (e) {
      this.translateService.get(['alert.virhe-kohdassa', translationKey],
        { value: this.getRecurringEntityFromDate(formArrIndex, entity) }).subscribe((res: any) => {
          this.ui.errorMessageInfo = res['alert.virhe-kohdassa'] + ': ' + res[translationKey];
          this.ui.showErrorMessageInfo = true;
        });
    }

    this.lapsiFormErrors = [];
    const errorMessageObj = this.vardaErrorMessageService.getErrorMessages(eObj);
    this.lapsiFormErrors = errorMessageObj.errorsArr;
    $('#henkiloModal .lapsi-form-content').scrollTop(0);
    this.ui.lapsiFormHasErrors = true;
    this.ui.isSubmitting = false;
    this.hideMessages();
  }

  onExpansionPanelClick($event: any, index: number, entityName: string): void {
    const entity = this.getExistingEntityByIndex(index, entityName);
    this.ui.lapsiFormSaveSuccess = false;
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      this.ui.openedVarhaiskasvatuspaatosIndex = index;
      this.preventClosingForUnsavedEntity($event, entity, this.varhaiskasvatuspaatosPanels, index);
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      this.ui.openedVarhaiskasvatussuhdeIndex = index;
      this.preventClosingForUnsavedEntity($event, entity, this.varhaiskasvatussuhdePanels, index);
    }
  }

  preventClosingForUnsavedEntity($event: Event, entity: any, panels: any, index: number) {
    if (!entity) {
      $event.stopPropagation();
      const currentPanels = panels.toArray();
      currentPanels[index].open();
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.isEdit && changes.henkilo) {
      this.currentLapsi = null;
      this.currentToimipaikka = this.vardaVakajarjestajaService.getSelectedToimipaikka();
      if (changes.isEdit.currentValue) {
        this.ui.saveBtnText = 'label.generic-update';

        this.henkilo = changes.henkilo.currentValue;
        if (this.henkilo.lapsi && this.henkilo.lapsi.length > 1) {
          console.error('Multiple children on lapsi-form. This causes race condition. Using the first one.', this.henkilo.lapsi);
        }

        forkJoin([
          this.initExistingLapsiFormData(this.henkilo.lapsi[0]),
        ]).subscribe({
          next: (data) => {
            this.initLapsiFormFields();
            this.ui.noVarhaiskasvatustietoPrivileges = false;
          },
          error: () => {
            this.ui.noVarhaiskasvatustietoPrivileges = true;
            this.ui.isPerustiedotLoading = false;
          }
        });

      } else {
        this.ui.saveBtnText = 'label.generic-add';
        this.varhaiskasvatussuhteet = [];
        this.varhaiskasvatuspaatokset = [];
        this.selectedSuhdeFieldChange(VardaEntityNames.VARHAISKASVATUSSUHDE, { checked: true });
        this.initLapsiFormFields();
      }
    } else if (changes.henkilo && changes.henkilo.currentValue) {
      this.initLapsiFormFields();
    }
  }

  ngOnInit() {
    this.toimipaikkaAccess = this.authService.getUserAccess(this.currentToimipaikka.organisaatio_oid);
    this.ui.isPerustiedotLoading = true;
    this.lapsiForm = new FormGroup({});
    this.varhaiskasvatussuhteetForm = new FormGroup({});
    this.varhaiskasvatussuhdeForm = new FormGroup({});
    this.varhaiskasvatuspaatoksetForm = new FormGroup({});
    this.varhaiskasvatuspaatosForm = new FormGroup({});
  }

  getTallentajaVakajarjestajat(vakajarjestajat: Array<PaosToimintatietoDto>) {
    return vakajarjestajat
      .filter(vakajarjestaja => `${vakajarjestaja.paos_oikeus.tallentaja_organisaatio_id}` === `${this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id}`);
  }
}
