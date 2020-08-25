import {
  Component,
  ElementRef,
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
import { MatRadioButton } from '@angular/material/radio';
import { MatStep, MatStepper } from '@angular/material/stepper';
import {
  VardaEntityNames,
  VardaFieldSet,
  VardaKielipainotusDTO,
  VardaToimintapainotusDTO,
  VardaToimipaikkaDTO
} from '../../../utilities/models';
import { VardaFormService } from '../../../core/services/varda-form.service';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { forkJoin, fromEvent, Observable, Subject } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaLocalstorageWrapperService } from '../../../core/services/varda-localstorage-wrapper.service';
import { VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { TranslateService } from '@ngx-translate/core';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { KoodistoDTO, KoodistoEnum, KoodistoSortBy, VardaKoodistoService } from 'varda-shared';

declare var $: any;

@Component({
  selector: 'app-varda-toimipaikka-form',
  templateUrl: './varda-toimipaikka-form.component.html',
  styleUrls: ['./varda-toimipaikka-form.component.css']
})
export class VardaToimipaikkaFormComponent implements OnInit, OnChanges {

  @Input() toimipaikka: VardaToimipaikkaDTO;
  @Input() isEdit: boolean;
  @Input() isReadOnly: boolean;
  @Output() saveToimipaikkaFormSuccess: EventEmitter<any> = new EventEmitter();
  @Output() valuesChanged: EventEmitter<boolean> = new EventEmitter();

  @ViewChild('formContent') formContent: ElementRef;
  @ViewChild('toimipaikkaStepper') toimipaikkaStepper: MatStepper;
  @ViewChild('kielipainotuksetYes') kielipainotuksetYes: MatRadioButton;
  @ViewChild('toimintapainotuksetYes') toimintapainotuksetYes: MatRadioButton;
  @ViewChildren('kielipainotuksetPanels') kielipainotuksetPanels: any;
  @ViewChildren('toimintapainotuksetPanels') toimintapainotuksetPanels: any;

  currentStep: MatStep;
  formTitle: string;
  toimipaikkaForm: FormGroup;
  toimipaikkaFieldSets: Array<VardaFieldSet>;
  toimintapainotuksetForm: FormGroup;
  toimintapainotuksetFieldSets: Array<VardaFieldSet>;
  kielipainotuksetForm: FormGroup;
  kielipainotuksetFieldSets: Array<VardaFieldSet>;

  toimipaikkaFormErrors: Array<any>;

  kielipainotukset: Array<VardaKielipainotusDTO>;
  toimintapainotukset: Array<VardaToimintapainotusDTO>;

  toimipaikkaFormChanged: boolean;
  kielipainotuksetFormChanged: boolean;
  toimintapainotuksetFormChanged: boolean;
  toimipaikkaAccess: UserAccess;
  kielikoodistoOptions: any;

  ui: {
    isSubmitting: boolean,
    toimipaikkaFormSaveSuccess: boolean,
    toimipaikkaFormHasErrors: boolean,
    formSaveSuccessMsg: string,
    formSaveFailureMsg: string,
    showKielipainotusAllDeleteWarning: boolean,
    showToimintapainotusAllDeleteWarning: boolean,
    showKielipainotusDeleteWarning: boolean,
    showToimintapainotusDeleteWarning: boolean
    selectedKielipainotusIndexToDelete: number,
    selectedToimintapainotusIndexToDelete: number,
    showKielipainotusSwitchIncorrectMsg: boolean,
    showToimintapainotusSwitchIncorrectMsg: boolean,
    kielipainotusSwitchIncorrectMsg: string,
    toimintapainotusSwitchIncorrectMsg: string,
    openedKielipainotusIndex: number,
    openedToimintapainotusIndex: number,
    showFormContinuesWarning: boolean,
    showKielipainotusFormContinuesWarning: boolean,
    showToimintapainotusFormContinuesWarning: boolean,
    showErrorMessageInfo: boolean,
    errorMessageInfo: string
  };

  private saveToimipaikkaSubject = new Subject<any>();
  private kieliKoodisto: KoodistoDTO;
  private toimintapainotusKoodisto: KoodistoDTO;

  constructor(
    private authService: AuthService,
    private vardaFormService: VardaFormService,
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaUtilityService: VardaUtilityService,
    private vardaModalService: VardaModalService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaLocalStorageWrapperService: VardaLocalstorageWrapperService,
    private vardaErrorMessageService: VardaErrorMessageService,
    private translateService: TranslateService,
    private koodistoService: VardaKoodistoService) {
    this.ui = {
      isSubmitting: false,
      toimipaikkaFormSaveSuccess: false,
      toimipaikkaFormHasErrors: false,
      formSaveSuccessMsg: '',
      formSaveFailureMsg: '',
      showKielipainotusAllDeleteWarning: false,
      showToimintapainotusAllDeleteWarning: false,
      showKielipainotusDeleteWarning: false,
      showToimintapainotusDeleteWarning: false,
      selectedKielipainotusIndexToDelete: null,
      selectedToimintapainotusIndexToDelete: null,
      showKielipainotusSwitchIncorrectMsg: false,
      showToimintapainotusSwitchIncorrectMsg: false,
      kielipainotusSwitchIncorrectMsg: '',
      toimintapainotusSwitchIncorrectMsg: '',
      openedKielipainotusIndex: null,
      openedToimintapainotusIndex: null,
      showFormContinuesWarning: false,
      showKielipainotusFormContinuesWarning: false,
      showToimintapainotusFormContinuesWarning: false,
      showErrorMessageInfo: false,
      errorMessageInfo: '',
    };

    this.vardaModalService.modalOpenObs('toimipaikkaSuccessModal').subscribe((isOpen: boolean) => {
      if (isOpen) {
        $(`#toimipaikkaSuccessModal`).modal({ keyboard: true, focus: true });
        setTimeout(() => {
          $(`#toimipaikkaSuccessModal`).modal('hide');
        }, 2000);
      }
    });
  }

  addNewKielipainotus(): void {
    const kielipainotusFormArr = <FormArray>this.kielipainotuksetForm.get('kielipainotusFormArr');
    this.ui.openedKielipainotusIndex = kielipainotusFormArr.length;
    kielipainotusFormArr.push(this.vardaFormService.initFieldSetFormGroup(this.kielipainotuksetFieldSets, null));
  }

  addNewToimintapainotus(): void {
    const toimintapainotusFormArr = <FormArray>this.toimintapainotuksetForm.get('toimintapainotusFormArr');
    this.ui.openedToimintapainotusIndex = toimintapainotusFormArr.length;
    toimintapainotusFormArr.push(this.vardaFormService.initFieldSetFormGroup(this.toimintapainotuksetFieldSets, null));
  }

  painotusFieldChange(entity: string, data: any): void {
    const painotusValue = data.value;
    const putData = this.getToimipaikkaFormData();
    let painotusFormRadio, painotusFormArr;
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      painotusFormRadio = this.kielipainotuksetForm.get('kielipainotukset_enabled');
      putData['kielipainotus_kytkin'] = painotusValue;
      painotusFormArr = <FormArray>this.kielipainotuksetForm.get('kielipainotusFormArr');
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      painotusFormRadio = this.toimintapainotuksetForm.get('toimintapainotukset_enabled');
      putData['toiminnallinenpainotus_kytkin'] = painotusValue;
      painotusFormArr = <FormArray>this.toimintapainotuksetForm.get('toimintapainotusFormArr');
    }

    painotusFormArr.controls = [];
    painotusFormArr.updateValueAndValidity();

    this.vardaApiWrapperService.saveToimipaikka(true, this.toimipaikka, putData).subscribe(() => {
      painotusFormRadio.setValue(painotusValue);
      this.saveToimipaikkaFormSuccess.emit(true);
    }, () => { }, () => {
      if (entity === VardaEntityNames.KIELIPAINOTUS) {
        this.kielipainotuksetFormChanged = false;
      } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
        this.toimintapainotuksetFormChanged = false;
      }
      this.checkIfAnyOfTheFormsHasChanged();
    });

    this.updatePainotusSwitchMessages(entity);
  }

  confirmDeletePainotusEntity(formArrIndex: number, showMsg: boolean, entity: string): void {
    let painotusEntityToEdit,
      painotusEntities,
      painotusFormArr,
      selectedPainotusIndexToDelete,
      painotusFormRadio,
      patchData,
      successMsg;
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      painotusEntityToEdit = this.kielipainotukset[formArrIndex];
      painotusEntities = this.kielipainotukset;
      painotusFormArr = <FormArray>this.kielipainotuksetForm.get('kielipainotusFormArr');
      selectedPainotusIndexToDelete = 'selectedKielipainotusIndexToDelete';
      painotusFormRadio = this.kielipainotuksetForm.get('kielipainotukset_enabled');
      patchData = {
        kielipainotus_kytkin: false
      };
      successMsg = 'alert.delete-kielipainotus-success';
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      painotusEntityToEdit = this.toimintapainotukset[formArrIndex];
      painotusEntities = this.toimintapainotukset;
      painotusFormArr = <FormArray>this.toimintapainotuksetForm.get('toimintapainotusFormArr');
      selectedPainotusIndexToDelete = 'selectedToimintapainotusIndexToDelete';
      painotusFormRadio = this.toimintapainotuksetForm.get('toimintapainotukset_enabled');
      patchData = {
        toiminnallinenpainotus_kytkin: false
      };
      successMsg = 'alert.delete-toimintapainotus-success';
    }

    if (painotusEntityToEdit) {
      this.ui.isSubmitting = true;
      this.ui.toimipaikkaFormHasErrors = false;
      const id = this.vardaUtilityService.parseIdFromUrl(painotusEntityToEdit.url);
      this.getDeletePainotusObservable(id, entity).subscribe((data) => {
        const indexToRemove = painotusEntities.findIndex((item) => item.url === painotusEntityToEdit.url);
        painotusEntities.splice(indexToRemove, 1);
        this.ui[selectedPainotusIndexToDelete] = null;
        painotusFormArr.removeAt(formArrIndex);
        if (showMsg) {
          this.ui.formSaveSuccessMsg = successMsg;
          this.ui.toimipaikkaFormSaveSuccess = true;
          this.hideMessages();
        }

        if (painotusFormArr.length === 0) {
          painotusFormRadio.setValue(false);
          if (this.isEdit) {
            setTimeout(() => {
              this.patchPainotuskytkin(entity, this.toimipaikka, patchData);
            }, 3000);
          }
        }
        this.ui.isSubmitting = false;
      }, this.onSaveError.bind(this, formArrIndex, entity));
    } else {
      painotusFormArr.removeAt(formArrIndex);
      this.ui[selectedPainotusIndexToDelete] = null;
    }
  }

  cancelDelete(entity: string): void {
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      this.ui.selectedKielipainotusIndexToDelete = null;
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      this.ui.selectedToimintapainotusIndexToDelete = null;
    }
  }

  closeForm(): void {
    $('#toimipaikkaModal').modal('hide');
    this.vardaModalService.openModal('toimipaikkaSuccessModal', true);
  }

  exitToimipaikkaForm(): void {
    this.valuesChanged.emit(false);
    this.closeForm();
  }

  displayDeleteWarning(entity: string, formArrIndex: number): void {
    let entityToEdit;
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      entityToEdit = this.kielipainotukset[formArrIndex];
      if (!entityToEdit) {
        this.confirmDeletePainotusEntity(formArrIndex, false, VardaEntityNames.KIELIPAINOTUS);
        return;
      }
      this.ui.selectedKielipainotusIndexToDelete = formArrIndex;
      setTimeout(() => $(`#kielipainotusCancelDeleteBtn${formArrIndex}`).focus());
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      entityToEdit = this.toimintapainotukset[formArrIndex];
      if (!entityToEdit) {
        this.confirmDeletePainotusEntity(formArrIndex, false, VardaEntityNames.TOIMINTAPAINOTUS);
        return;
      }
      this.ui.selectedToimintapainotusIndexToDelete = formArrIndex;
      setTimeout(() => $(`#toimintapainotusCancelDeleteBtn${formArrIndex}`).focus());
    }
  }

  hideMessages(): void {
    setTimeout(() => {
      this.ui.toimipaikkaFormSaveSuccess = false;
    }, 3500);
  }

  getDeletePainotusObservable(id: string, entity: string): Observable<any> {
    let obs;
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      obs = this.vardaApiWrapperService.deleteKielipainotus(id);
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      obs = this.vardaApiWrapperService.deleteToimintapainotus(id);
    }
    return obs;
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

    if (entityName === VardaEntityNames.KIELIPAINOTUS) {
      entity = this.kielipainotukset[index];
    } else if (entityName === VardaEntityNames.TOIMINTAPAINOTUS) {
      entity = this.toimintapainotukset[index];
    }

    if (entity) {
      rv += ' varda-button-danger';
    } else {
      rv += ' varda-button-neutral';
    }

    return rv;
  }

  getDeleteKielipainotusText(index: number): string {
    const kielipainotusToEdit = this.kielipainotukset[index];
    if (!kielipainotusToEdit) {
      return 'label.cancel';
    } else {
      return 'label.delete';
    }
  }

  getDeleteToimintapainotusText(index: number): string {
    const toimintapainotusToEdit = this.toimintapainotukset[index];
    if (!toimintapainotusToEdit) {
      return 'label.cancel';
    } else {
      return 'label.delete';
    }
  }

  getSaveKielipainotusText(index: number): string {
    const kielipainotusToEdit = this.kielipainotukset[index];
    if (!kielipainotusToEdit) {
      return 'label.generic-save';
    } else {
      return 'label.generic-save';
    }
  }

  getSaveToimintapainotusText(index: number): string {
    const toimintapainotusToEdit = this.toimintapainotukset[index];
    if (!toimintapainotusToEdit) {
      return 'label.generic-save';
    } else {
      return 'label.generic-save';
    }
  }

  getToimipaikkaFormData(): any {
    const data = {
      toimipaikka: { formData: {}, fieldSets: {} }
    };
    const toimipaikkaFormData = this.toimipaikkaForm.getRawValue();
    const toimipaikkaFormDataKeys = Object.keys(toimipaikkaFormData);
    const someKey = toimipaikkaFormDataKeys.pop();
    const kielipainotusEnabled = this.kielipainotuksetForm.get('kielipainotukset_enabled').value;
    const toimintapainotusEnabled = this.toimintapainotuksetForm.get('toimintapainotukset_enabled').value;
    toimipaikkaFormData[someKey]['kielipainotus_kytkin'] = !!kielipainotusEnabled;
    toimipaikkaFormData[someKey]['toiminnallinenpainotus_kytkin'] = !!toimintapainotusEnabled;
    data.toimipaikka.formData = toimipaikkaFormData;
    data.toimipaikka.fieldSets = this.toimipaikkaFieldSets;
    return data;
  }

  getKielipainotusFormData(index: number): any {
    const data = {
      kielipainotus: { formData: {}, fieldSets: {} }
    };
    const kielipainotusFormArr = <FormArray>this.kielipainotuksetForm.get('kielipainotusFormArr');
    const fg = kielipainotusFormArr.at(index);
    data.kielipainotus.formData = fg.value;
    data.kielipainotus.fieldSets = this.kielipainotuksetFieldSets;
    return data;
  }

  getToimintapainotusFormData(index: number): any {
    const data = {
      toimintapainotus: { formData: {}, fieldSets: {} }
    };

    const toimintapainotusFormArr = <FormArray>this.toimintapainotuksetForm.get('toimintapainotusFormArr');
    const fg = toimintapainotusFormArr.at(index);
    data.toimintapainotus.formData = fg.value;
    data.toimintapainotus.fieldSets = this.toimintapainotuksetFieldSets;
    return data;
  }

  getRecurringFieldValue(entity: string, index: number): string {
    let rv = '';
    let code;
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      const foundKielipainotus = this.kielipainotukset[index];
      if (foundKielipainotus) {
        rv += foundKielipainotus.kielipainotus_koodi;
        code = this.kieliKoodisto.codes.find(kieliCode => {
          return kieliCode.code_value.toLowerCase() === foundKielipainotus.kielipainotus_koodi.toLowerCase();
        });
      }
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      const foundToimintapainotus = this.toimintapainotukset[index];
      if (foundToimintapainotus) {
        rv += foundToimintapainotus.toimintapainotus_koodi;
        code = this.toimintapainotusKoodisto.codes.find(toimintapainotus => {
          return foundToimintapainotus.toimintapainotus_koodi.toLowerCase() === toimintapainotus.code_value.toLowerCase();
        });
      }
    }

    if (!code) {
      return '';
    }
    rv = `${code.name} (${code.code_value})`;

    return rv;
  }

  getNextButtonText(): string {
    const translationKey = 'label.generic-save';
    return translationKey;
  }

  initToimipaikkaFormFields(): void {
    forkJoin([
      this.vardaApiWrapperService.getToimipaikkaFormFieldSets(),
      this.koodistoService.getKoodisto(KoodistoEnum.kunta, KoodistoSortBy.name),
      this.koodistoService.getKoodisto(KoodistoEnum.kieli, KoodistoSortBy.name),
      this.koodistoService.getKoodisto(KoodistoEnum.kasvatusopillinenjarjestelma),
      this.koodistoService.getKoodisto(KoodistoEnum.toimintamuoto),
      this.koodistoService.getKoodisto(KoodistoEnum.jarjestamismuoto),
      this.koodistoService.getKoodisto(KoodistoEnum.toiminnallinenpainotus)
    ]).subscribe(([formData, kuntaKoodisto, kieliKoodisto, kasvatusjarjestelmaKoodisto,
                        toimintamuotoKoodisto, jarjestamismuotoKoodisto, toimintapainotusKoodisto]) => {
      this.toimintapainotusKoodisto = <KoodistoDTO> toimintapainotusKoodisto;
      this.kieliKoodisto = <KoodistoDTO> kieliKoodisto;
      VardaKoodistoService.sortKieliKoodistoByPrimaryLanguages(this.kieliKoodisto);

      // Update codes used in this form
      [
        { fields: formData[0].fieldsets[1].fields, key: 'kunta_koodi', koodisto: kuntaKoodisto },
        { fields: formData[0].fieldsets[2].fields, key: 'toimintamuoto_koodi', koodisto: toimintamuotoKoodisto },
        { fields: formData[0].fieldsets[2].fields, key: 'jarjestamismuoto_koodi', koodisto: jarjestamismuotoKoodisto },
        { fields: formData[0].fieldsets[2].fields, key: 'kasvatusopillinen_jarjestelma_koodi', koodisto: kasvatusjarjestelmaKoodisto },
        { fields: formData[0].fieldsets[2].fields, key: 'asiointikieli_koodi', koodisto: this.kieliKoodisto },
        { fields: formData[1].fieldsets[0].fields, key: 'kielipainotus_koodi', koodisto: this.kieliKoodisto },
        { fields: formData[2].fieldsets[0].fields, key: 'toimintapainotus_koodi', koodisto: this.toimintapainotusKoodisto }
      ].forEach(fieldsObject => VardaKoodistoService.updateOptionsIfFound(fieldsObject.fields, fieldsObject.key, fieldsObject.koodisto));

      this.toimipaikkaFieldSets = formData[0].fieldsets;
      this.toimipaikkaForm = this.vardaFormService.initFieldSetFormGroup(this.toimipaikkaFieldSets, this.toimipaikka);

      this.kielipainotuksetFieldSets = formData[1].fieldsets;
      this.kielipainotuksetForm = new FormGroup({});
      const kielipainotusFormArr = new FormArray([]);

      this.toimintapainotuksetFieldSets = formData[2].fieldsets;
      this.toimintapainotuksetForm = new FormGroup({});
      const toimintapainotusFormArr = new FormArray([]);

      if (this.kielipainotukset.length > 0) {
        this.kielipainotukset.forEach((kielipainotusItem) => {
          kielipainotusFormArr.push(this.vardaFormService.initFieldSetFormGroup(this.kielipainotuksetFieldSets, kielipainotusItem));
        });
      }

      if (this.toimintapainotukset.length > 0) {
        this.toimintapainotukset.forEach((toimintapainotusItem) => {
          toimintapainotusFormArr.push(this.vardaFormService.initFieldSetFormGroup(
            this.toimintapainotuksetFieldSets, toimintapainotusItem));
        });
      }

      let kielipainotuskytkin_enabled = false;
      if (this.toimipaikka && this.toimipaikka.kielipainotus_kytkin) {
        kielipainotuskytkin_enabled = true;
      }

      let toimintapainotuskytkin_enabled = false;
      if (this.toimipaikka && this.toimipaikka.toiminnallinenpainotus_kytkin) {
        toimintapainotuskytkin_enabled = true;
      }

      this.kielipainotuksetForm.addControl('kielipainotusFormArr', kielipainotusFormArr);
      this.kielipainotuksetForm.addControl('kielipainotukset_enabled', new FormControl({
        value: kielipainotuskytkin_enabled,
        disabled: this.isReadOnly,
      }));
      this.toimintapainotuksetForm.addControl('toimintapainotusFormArr', toimintapainotusFormArr);
      this.toimintapainotuksetForm.addControl('toimintapainotukset_enabled', new FormControl({
        value: toimintapainotuskytkin_enabled,
        disabled: this.isReadOnly,
      }));

      this.toimipaikkaForm.valueChanges.subscribe((d) => {
        if (this.toimipaikkaForm.dirty) {
          this.toimipaikkaFormChanged = true;
          this.checkIfAnyOfTheFormsHasChanged();
        }
      });

      this.kielipainotuksetForm.valueChanges.subscribe((d) => {
        if (this.kielipainotuksetForm.dirty) {
          this.kielipainotuksetFormChanged = true;
          this.checkIfAnyOfTheFormsHasChanged();
        }
      });

      this.toimintapainotuksetForm.valueChanges.subscribe((d) => {
        if (this.toimintapainotuksetForm.dirty) {
          this.toimintapainotuksetFormChanged = true;
          this.checkIfAnyOfTheFormsHasChanged();
        }
      });

      this.bindHideSuccessMsg();
      this.bindScrollHandlers();
    });
  }

  bindHideSuccessMsg(): void {
    setTimeout(() => {
      $('.varda-button, .varda-form-control, .varda-date, .varda-radio, .varda-mat-checkbox').click(() => {
        this.ui.toimipaikkaFormSaveSuccess = false;
      });
    }, 2000);
  }

  bindScrollHandlers(): void {
    fromEvent(this.formContent.nativeElement, 'scroll')
      .pipe(debounceTime(300))
      .subscribe((e: any) => {
        const ct = e.target;
        this.ui.showFormContinuesWarning = ct.scrollHeight - ct.clientHeight - ct.scrollTop > 200;
      });
  }

  checkIfAnyOfTheFormsHasChanged(): void {
    let rv = false;
    if (this.toimipaikkaFormChanged || this.kielipainotuksetFormChanged || this.toimintapainotuksetFormChanged) {
      rv = true;
    }
    this.valuesChanged.emit(rv);
  }

  initExistingToimipaikkaFormData(): Observable<any> {
    return new Observable((observer) => {
      const toimipaikkaId = this.vardaUtilityService.parseIdFromUrl(this.toimipaikka.url);
      forkJoin([
        this.vardaApiWrapperService.getKielipainotuksetByToimipaikka(toimipaikkaId),
        this.vardaApiWrapperService.getToimintapainotuksetByToimipaikka(toimipaikkaId),
      ]).subscribe((data) => {
        this.kielipainotukset = data[0];
        this.toimintapainotukset = data[1];
        this.toimipaikkaAccess = this.authService.getUserAccess(this.toimipaikka.organisaatio_oid);
        this.isReadOnly = this.isReadOnly || !this.toimipaikkaAccess.lapsitiedot.tallentaja;
        observer.next();
        observer.complete();
      });
    });
  }

  patchPainotuskytkin(entity: string, toimipaikka: VardaToimipaikkaDTO, data: any): void {
    let painotusFormRadio;
    const putData = Object.assign(this.getToimipaikkaFormData(), data);
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      painotusFormRadio = this.kielipainotuksetForm.get('kielipainotukset_enabled');
      this.vardaApiWrapperService.saveToimipaikka(true, this.toimipaikka, putData).subscribe(() => {
        painotusFormRadio.setValue(data['kielipainotus_kytkin']);
        this.saveToimipaikkaFormSuccess.emit(true);
      }, () => { }, () => setTimeout(() => {
        this.kielipainotuksetFormChanged = false;
        this.checkIfAnyOfTheFormsHasChanged();
      }, 500));
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      painotusFormRadio = this.toimintapainotuksetForm.get('toimintapainotukset_enabled');
      this.vardaApiWrapperService.saveToimipaikka(true, this.toimipaikka, putData).subscribe(() => {
        painotusFormRadio.setValue(data['toiminnallinenpainotus_kytkin']);
        this.saveToimipaikkaFormSuccess.emit(true);
      }, () => { }, () => setTimeout(() => {
        this.toimintapainotuksetFormChanged = false;
        this.checkIfAnyOfTheFormsHasChanged();
      }, 500));
    }
  }

  updatePainotusSwitchMessages(entityName: string): void {
    const kielipainotusFormRadioValue = this.kielipainotuksetForm.get('kielipainotukset_enabled').value;
    const toimintapainotusFormRadioValue = this.toimintapainotuksetForm.get('toimintapainotukset_enabled').value;
    if (entityName === VardaEntityNames.KIELIPAINOTUS) {
      const kielipainotusSwitchInCorrect = kielipainotusFormRadioValue && this.kielipainotukset.length === 0;
      this.ui.showKielipainotusSwitchIncorrectMsg = kielipainotusSwitchInCorrect;
    } else if (entityName === VardaEntityNames.TOIMINTAPAINOTUS) {
      const toimintapainotusSwitchInCorrect = toimintapainotusFormRadioValue && this.toimintapainotukset.length === 0;
      this.ui.showToimintapainotusSwitchIncorrectMsg = toimintapainotusSwitchInCorrect;
    }
  }

  saveKielipainotus(formArrIndex: number): void {
    this.ui.toimipaikkaFormHasErrors = false;
    this.ui.isSubmitting = true;
    const formData = this.getKielipainotusFormData(formArrIndex);
    let isEdit = false;
    const kielipainotusToEdit = this.kielipainotukset[formArrIndex];
    if (kielipainotusToEdit) {
      isEdit = true;
    }

    this.vardaApiWrapperService.saveKielipainotus(isEdit, this.toimipaikka,
      kielipainotusToEdit, formData).subscribe({
        next: this.onSaveSuccess.bind(this, 'kielipainotus', formArrIndex, isEdit),
        error: this.onSaveError.bind(this, formArrIndex, 'kielipainotus'),
      });
  }

  saveToimintapainotus(formArrIndex: number): void {
    this.ui.toimipaikkaFormHasErrors = false;
    this.ui.isSubmitting = true;
    const formData = this.getToimintapainotusFormData(formArrIndex);
    let isEdit = false;
    const toimintapainotusToEdit = this.toimintapainotukset[formArrIndex];
    if (toimintapainotusToEdit) {
      isEdit = true;
    }
    this.vardaApiWrapperService.saveToimintapainotus(isEdit, this.toimipaikka, toimintapainotusToEdit, formData)
      .subscribe({
        next: this.onSaveSuccess.bind(this, 'toimintapainotus', formArrIndex, isEdit),
        error: this.onSaveError.bind(this, formArrIndex, 'toimintapainotus'),
      });
  }

  saveToimipaikka(): void {
    this.ui.toimipaikkaFormHasErrors = false;
    this.ui.isSubmitting = true;
    const formData = this.getToimipaikkaFormData();
    this.vardaApiWrapperService.saveToimipaikka(this.isEdit, this.toimipaikka, formData)
      .subscribe({
        next: this.onSaveSuccess.bind(this, 'toimipaikka', null, null),
        error: this.onSaveError.bind(this, null, null),
      });
  }

  onSaveSuccess(...args): void {
    setTimeout(() => {
      const action = args[0];
      const formArrIndex = args[1];
      const isEdit = args[2];
      const entity = args[3];

      let currentPanels;
      let painotusArr;

      if (action === 'kielipainotus') {
        this.kielipainotuksetFormChanged = false;
        currentPanels = this.kielipainotuksetPanels.toArray();
        currentPanels[formArrIndex].close();
        painotusArr = this.kielipainotukset;
      } else if (action === 'toimintapainotus') {
        this.toimintapainotuksetFormChanged = false;
        currentPanels = this.toimintapainotuksetPanels.toArray();
        currentPanels[formArrIndex].close();
        painotusArr = this.toimintapainotukset;
      } else if (action === 'toimipaikka') {
        if (!this.isEdit) {
          this.isEdit = true;
          const toimipaikanNimiFc = this.vardaFormService.findFormControlFromFormGroupByFieldKey('nimi', this.toimipaikkaForm);
          const toimipaikanToimintamuotoFc = this.vardaFormService.findFormControlFromFormGroupByFieldKey('toimintamuoto_koodi',
            this.toimipaikkaForm);
          toimipaikanNimiFc.disable();
          toimipaikanToimintamuotoFc.disable();
        }

        this.formTitle = entity.nimi;
        this.toimipaikkaFormChanged = false;

        this.toimipaikka = entity;
        this.vardaVakajarjestajaService.setSelectedToimipaikka(entity);
        this.vardaLocalStorageWrapperService.saveToLocalStorage('varda.activeToimipaikka', JSON.stringify(entity));
        this.saveToimipaikkaFormSuccess.emit({ toimipaikka: entity });
      }

      if (painotusArr && !isEdit) {
        painotusArr.push(entity);
      } else if (painotusArr && isEdit) {
        painotusArr[formArrIndex] = entity;
      }

      this.ui.formSaveSuccessMsg = 'alert.modal-generic-save-success';
      this.ui.toimipaikkaFormSaveSuccess = true;
      this.checkIfAnyOfTheFormsHasChanged();
      this.updatePainotusSwitchMessages(entity);
      this.ui.isSubmitting = false;

      setTimeout(() => this.kielipainotuksetYes.focus(), 500);

    }, 1000);
  }

  onSaveError(...args): void {
    this.ui.formSaveFailureMsg = '';
    this.toimipaikkaFormErrors = [];
    const formArrIndex = args[0];
    const entity = args[1];
    const eObj = args[2];

    let msgForAlert = '';
    let e, painotusErrorValue;
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      e = this.kielipainotukset[formArrIndex];
      painotusErrorValue = this.getRecurringFieldValue(entity, formArrIndex);
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      e = this.toimintapainotukset[formArrIndex];
      painotusErrorValue = this.getRecurringFieldValue(entity, formArrIndex);
    }

    if (e) {
      this.translateService.get(['alert.virhe-kohdassa']).subscribe((res: any) => {
        this.ui.errorMessageInfo = res['alert.virhe-kohdassa'] + ': ' + painotusErrorValue;
        this.ui.showErrorMessageInfo = true;
      });
    }

    const errorMessageObj = this.vardaErrorMessageService.getErrorMessages(eObj);
    this.toimipaikkaFormErrors = errorMessageObj.errorsArr;
    msgForAlert = errorMessageObj.alertMsg;

    $('#toimipaikkaModal .toimipaikka-form-content').scrollTop(0);
    this.ui.toimipaikkaFormHasErrors = true;
    this.ui.isSubmitting = false;
    this.hideMessages();
  }

  onExpansionPanelOpen($event: any, index: number, entity: string): void {
    this.ui.toimipaikkaFormSaveSuccess = false;
    if (entity === VardaEntityNames.KIELIPAINOTUS) {
      this.ui.openedKielipainotusIndex = index;
    } else if (entity === VardaEntityNames.TOIMINTAPAINOTUS) {
      this.ui.openedToimintapainotusIndex = index;
    }

  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.isEdit && changes.toimipaikka) {
      if (changes.isEdit.currentValue) {
        this.formTitle = this.toimipaikka.nimi;
        this.initExistingToimipaikkaFormData().subscribe((data) => {
          this.initToimipaikkaFormFields();
        });
      } else {
        this.formTitle = 'label.add-toimipaikka';
        this.toimipaikka = null;
        this.kielipainotukset = [];
        this.toimintapainotukset = [];
        this.initToimipaikkaFormFields();
      }
    }
  }

  ngOnInit() {
    this.toimipaikkaForm = new FormGroup({});
    this.kielipainotuksetForm = new FormGroup({});
    this.toimintapainotuksetForm = new FormGroup({});
  }

}
