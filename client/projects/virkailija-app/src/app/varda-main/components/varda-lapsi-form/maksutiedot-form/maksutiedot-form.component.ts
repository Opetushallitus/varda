import { Component, ElementRef, Input, OnInit, QueryList, ViewChild, ViewChildren, Output, EventEmitter } from '@angular/core';
import { AbstractControl, FormArray, FormControl, FormGroup } from '@angular/forms';
import { HuoltajaDTO, VardaCreateMaksutietoDTO, VardaMaksutietoDTO } from '../../../../utilities/models/dto/varda-maksutieto-dto.model';
import { MatExpansionPanel } from '@angular/material/expansion';
import { VardaFieldSet, VardaFieldsetArrayContainer } from '../../../../utilities/models/varda-fieldset.model';
import { VardaApiWrapperService } from '../../../../core/services/varda-api-wrapper.service';
import { VardaFormService } from '../../../../core/services/varda-form.service';
import { forkJoin, Observable } from 'rxjs';
import { VardaUtilityService } from '../../../../core/services/varda-utility.service';
import { VardaValidatorService } from '../../../../core/services/varda-validator.service';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaDateService } from '../../../services/varda-date.service';
import { VardaErrorMessageService } from '../../../../core/services/varda-error-message.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { map } from 'rxjs/operators';
import { KoodistoDTO, KoodistoEnum, VardaKoodistoService } from 'varda-shared';

@Component({
  selector: 'app-maksutiedot-form',
  templateUrl: './maksutiedot-form.component.html',
  styleUrls: ['./maksutiedot-form.component.css']
})
export class MaksutiedotFormComponent implements OnInit {
  private _isLapsiYksityinen: boolean;
  @Input() lapsiId;
  @Input() set isLapsiYksityinen(lapsiIsYksityinen: boolean) {
    this._isLapsiYksityinen = lapsiIsYksityinen;
    this.removeFieldsForYksityinenLapsi();
  }
  @Input() toimipaikkaAccess: UserAccess;
  @Input() hideMaksutiedot: boolean;

  // For accessing template reference variables
  @ViewChildren('maksutietoPanels') maksutietoPanels: QueryList<MatExpansionPanel>;
  @ViewChildren('maksutietoCancelDeleteBtn') maksutietoCancelDeleteButtons: QueryList<HTMLButtonElement>;
  @ViewChildren('recurringMaksutietoEntityHeader') recurringMaksutietoEntityHeader: QueryList<HTMLDivElement>;
  @ViewChild('notificationContainer') notificationContainer: ElementRef<HTMLDivElement>;

  maksutiedotFormGroup: FormGroup;
  ui: {
    noMaksutietoPrivileges: boolean;
    formSaveErrors: Array<{ key: string, msg: string, }>;
    formSaveErrorMsg: string;
    formSaveSuccessMsg: string;
    isLoading: boolean;
    openedMaksutietoIndex: number,
    indexOfMaksutietoToDelete: number,
    showMaksutietoFormContinuesTextWrapper: boolean,
    scrollOnInit: ElementRef<HTMLDivElement>,
    showSaveButton: boolean
  };
  maksutiedot: Array<VardaMaksutietoDTO>;
  // template for creating new one
  maksutiedotFieldSetTemplate: VardaFieldsetArrayContainer;
  // fieldset obj for editing
  maksutiedotFieldSetObj: { [key: string]: Array<VardaFieldSet> };

  constructor(
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaFormService: VardaFormService,
    private vardaUtilityService: VardaUtilityService,
    private vardaValidatorService: VardaValidatorService,
    private vardaApiService: VardaApiService,
    private translate: TranslateService,
    private vardaDateService: VardaDateService,
    private vardaErrorMessageService: VardaErrorMessageService,
    private authService: AuthService,
    private koodistoService: VardaKoodistoService
  ) {
    this.maksutiedotFieldSetObj = {};
    this.maksutiedotFormGroup = new FormGroup({
      maksutiedotFormArr: new FormArray([]),
    });
    this.maksutiedot = [];
    this.ui = {
      isLoading: false,
      openedMaksutietoIndex: null,
      showMaksutietoFormContinuesTextWrapper: false,
      indexOfMaksutietoToDelete: null,
      formSaveSuccessMsg: null,
      formSaveErrorMsg: null,
      formSaveErrors: [],
      scrollOnInit: null,
      noMaksutietoPrivileges: true,
      showSaveButton: false
    };
  }

  getInitialHuoltajat(idx: number): Array<HuoltajaDTO> {
    return this.maksutiedot[idx] && this.maksutiedot[idx].id
      ? this.maksutiedot[idx].huoltajat
      : [];
  }

  // FormGroup.get() returns AbstractControl so fix type
  get maksutiedotFormArr(): FormArray {
    return <FormArray>this.maksutiedotFormGroup.get('maksutiedotFormArr');
  }

  // FormGroup.get() returns AbstractControl so fix type
  getMaksutietoFormGroup(control: AbstractControl, id: string) {
    return <FormGroup>control.get(id);
  }

  ngOnInit() {
    if (this.toimipaikkaAccess.huoltajatiedot.katselija) {
      forkJoin([
        this.vardaApiWrapperService.getMaksutietoFormFieldSets(),
        this.vardaApiWrapperService.getLapsiMaksutiedot(this.lapsiId),
        this.koodistoService.getKoodisto(KoodistoEnum.maksunperuste)
      ]).subscribe({
        next: this.onInitFetchSuccess(),
        error: () => this.ui.noMaksutietoPrivileges = true,
      });
    }
  }

  private scrollToSelected() {
    if (this.ui.scrollOnInit) {
      this.ui.scrollOnInit.nativeElement.scrollIntoView({ behavior: 'smooth' });
      this.ui.scrollOnInit = null;
    }
  }

  private onInitFetchSuccess() {
    return ([maksutietoFieldsetData, maksutiedotData, koodistoData]) => {

      // Update codes used in this form
      VardaKoodistoService.updateOptionsIfFound(maksutietoFieldsetData[0].fieldsets[0].fields, 'maksun_peruste_koodi', koodistoData);

      this.maksutiedotFieldSetTemplate = maksutietoFieldsetData[0];
      this.removeFieldsForYksityinenLapsi();

      this.maksutiedot = maksutiedotData.sort((a, b) => new Date(a.alkamis_pvm).getTime() - new Date(b.alkamis_pvm).getTime());
      this.maksutiedot.forEach(maksutieto => {
        const koodi = maksutieto.maksun_peruste_koodi;
        maksutieto.maksun_peruste_koodi = koodi && koodi.toLowerCase();
      });
      const maksutiedotFormGroups = this.maksutiedot
        .map((maksutieto, idx) => this.createMaksutietoFormGroup(maksutieto, idx));
      this.maksutiedotFormGroup = new FormGroup({
        maksutiedotFormArr: new FormArray(maksutiedotFormGroups),
      });

      this.ui.isLoading = false;
      this.ui.noMaksutietoPrivileges = false;
    };
  }

  createMaksutietoFormGroup(maksutieto, idx) {
    const maksutietoFieldsets = this.vardaUtilityService.deepcopyArray(this.maksutiedotFieldSetTemplate.fieldsets);
    this.maksutiedotFieldSetObj[idx] = maksutietoFieldsets;
    const maksutietoFormgroup = this.vardaFormService.initFieldSetFormGroup(maksutietoFieldsets, maksutieto);
    this.vardaValidatorService.initFieldStates(maksutietoFieldsets, maksutietoFormgroup);
    maksutietoFormgroup.addControl('huoltajat', new FormControl(''));
    return maksutietoFormgroup;
  }

  onExpansionPanelClick($event: Event, index: number): void {
    const entity = this.maksutiedot[index];
    this.ui.openedMaksutietoIndex = index;
    this.preventClosingForUnsavedEntity($event, entity, this.maksutietoPanels, index);
  }

  // Stops from closing unsaved maksutieto form (unless other one is opened explicitly)
  preventClosingForUnsavedEntity(event: Event, entity: VardaMaksutietoDTO, panels: any, index: number) {
    if (!entity || !entity.id) {
      event.stopPropagation();
      const currentPanels = panels.toArray();
      currentPanels[index].open();
    } else {
      // Clear notifications when opening or closing existing maksutieto
      this.ui.formSaveSuccessMsg = null;
      this.clearErrorMessages();
    }
  }

  getMaksutietoHeader(index: number) {
    const entity = this.maksutiedot[index];
    if (entity && entity.id) {
      const alkupvm = this.vardaDateService.vardaDateToUIStrDate(entity.alkamis_pvm);
      const loppupvm = this.vardaDateService.vardaDateToUIStrDate(entity.paattymis_pvm);
      return entity.paattymis_pvm
        ? this.translate.get('label.maksutieto.muokkaa.otsikko-alkupvm-loppupvm', { alkupvm, loppupvm })
        : this.translate.get('label.maksutieto.muokkaa.otsikko-alkupvm', { alkupvm });
    }
    return this.translate.get('label.maksutieto.uusi.otsikko');
  }

  createNewMaksutietoForm() {
    const newMaksutietoForm = this.createMaksutietoFormGroup(null, this.maksutiedotFormArr.length);
    this.maksutiedotFormArr.push(newMaksutietoForm);
    this.ui.openedMaksutietoIndex = this.maksutiedotFormArr.value.length - 1;
  }

  saveMaksutiedot(idx: number) {
    this.ui.isLoading = true;
    const isCreateNew = !this.maksutiedot[idx] || !this.maksutiedot[idx].id;
    this.ui.scrollOnInit = this.notificationContainer;

    this.doSaveMaksutieto(idx, isCreateNew)
      .subscribe((maksutieto: VardaMaksutietoDTO) => {
        this.getCreatedSuccessMessage(maksutieto, isCreateNew)
          .subscribe(successMessage => {
            const delay = !isCreateNew ? 5000 : 10000;
            this.showSuccessAndHideAfterDelay(successMessage, delay);
            this.ui.openedMaksutietoIndex = null;
            // Reload the component (at least partially) on success
            this.ngOnInit();
          });
      }, this.onSaveError(idx))
      .add(() => {
        this.ui.isLoading = false;
        this.scrollToSelected();
      });
  }

  private getCreatedSuccessMessage(maksutieto: VardaMaksutietoDTO, isCreateNew: boolean) {
    const translationParams = {
      savedHuoltajaCount: maksutieto.tallennetut_huoltajat_count,
      notSavedHuoltajaCount: maksutieto.ei_tallennetut_huoltajat_count,
    };
    const translationKeys = ['alert.modal-generic-save-success', 'alert.maksutieto.success', 'alert.maksutieto.success-suffix'];
    return this.translate.get(translationKeys, translationParams).pipe(
      map(translations => {
        if (!isCreateNew) {
          return translations['alert.modal-generic-save-success'];
        }
        const successMessage = translations['alert.maksutieto.success'];
        return !translationParams.notSavedHuoltajaCount ? successMessage : `${successMessage} ${translations['alert.maksutieto.success-suffix']}`;
      }),
    );
  }

  private doSaveMaksutieto(idx: number, isCreateNew: boolean): Observable<VardaMaksutietoDTO> {
    const lapsiUri = VardaApiService.getLapsiUrlFromId(this.lapsiId);
    const dto = this.vardaApiWrapperService.createDTOwithData<VardaCreateMaksutietoDTO>(
      this.maksutiedotFormArr.value[idx],
      new VardaCreateMaksutietoDTO(),
      this.maksutiedotFieldSetObj[idx]);
    dto.maksun_peruste_koodi = dto.maksun_peruste_koodi && dto.maksun_peruste_koodi.toLowerCase();
    dto.palveluseteli_arvo = dto.palveluseteli_arvo || 0;
    dto.asiakasmaksu = dto.asiakasmaksu || 0;
    dto.lapsi = lapsiUri;
    dto.huoltajat = this.maksutiedot[idx].huoltajat;
    return isCreateNew
      ? this.vardaApiService.createMaksutieto(dto)
      : this.vardaApiService.updateMaksutieto(this.maksutiedot[idx].id, dto);
  }

  setHuoltajat($event: Array<HuoltajaDTO>, idx: number) {
    if (!this.maksutiedot[idx]) {
      this.maksutiedot[idx] = new VardaMaksutietoDTO();
    }
    this.maksutiedot[idx].huoltajat = $event;
  }

  getDeleteButtonStyles(idx: number) {
    const entity = this.maksutiedot[idx];
    const entityExists = !!entity && !!entity.id;
    return {
      'varda-disabled-button': this.ui.isLoading,
      'varda-button-danger': entityExists,
      'varda-button-neutral': !entityExists,
    };
  }

  displayDeleteWarning(idx: number) {
    const maksutietoToDelete = this.maksutiedot[idx];
    this.ui.indexOfMaksutietoToDelete = idx;
    this.maksutietoCancelDeleteButtons
      .filter(item => item.id === 'maksutietoCancelDeleteBtn' + idx)
      .forEach(item => item.focus());
    if (!maksutietoToDelete || !maksutietoToDelete.id) {
      this.ui.indexOfMaksutietoToDelete = null;
      this.doDeleteAction(idx);
    }
  }

  private doDeleteAction(idx: number) {
    const maksutietoToDelete = this.maksutiedot[idx];
    this.clearErrorMessages();

    if (maksutietoToDelete && maksutietoToDelete.id) {
      this.ui.isLoading = true;
      this.vardaApiService.deleteMaksutieto(maksutietoToDelete.id)
        .subscribe(() => {
          this.showSuccessAndHideAfterDelay('alert.delete-maksutieto-success');
          this.maksutiedot.splice(idx, 1);

          // Refresh component
          this.ngOnInit();
        }, this.onSaveError(idx))
        .add(() => {
          this.ui.isLoading = false;
          this.ui.scrollOnInit = this.notificationContainer;
          this.scrollToSelected();
        });
    } else {
      // No notifications are shown when removing unsaved maksutieto
      this.maksutiedotFormArr.removeAt(idx);
    }
    this.ui.indexOfMaksutietoToDelete = null;
  }

  getDeleteText(idx: number) {
    const maksutietoToDelete = this.maksutiedot[idx];
    if (!maksutietoToDelete || !maksutietoToDelete.id) {
      return 'label.cancel';
    }
    return 'label.delete';
  }

  cancelDelete() {
    this.ui.indexOfMaksutietoToDelete = null;
  }

  private showSuccessAndHideAfterDelay(messageToShow: string, delay = 5000) {
    this.clearErrorMessages();
    this.ui.formSaveSuccessMsg = messageToShow;
    setTimeout(() => {
      this.ui.formSaveSuccessMsg = null;
    }, delay);
  }

  private clearErrorMessages() {
    this.ui.formSaveErrorMsg = null;
    this.ui.formSaveErrors = [];
  }

  private onSaveError(idx: number) {
    return e => {
      if (e.status === 400) {
        forkJoin([
          this.translate.get('alert.virhe-kohdassa'),
          this.getMaksutietoHeader(idx),
        ]).subscribe(messages => {
          const [errorField, errorHeader] = messages;
          this.ui.formSaveErrorMsg = errorField + ': ' + errorHeader;
          this.ui.formSaveErrors = this.vardaErrorMessageService.getErrorMessages(e).errorsArr;
        });
      } else {
        // This could contain stacktrace so we give generic message instead
        this.translate.get('alert.modal-generic-save-error').subscribe(genericErrorMsg => {
          this.ui.formSaveErrorMsg = genericErrorMsg;
          this.ui.formSaveErrors = [];
        });
      }
    };
  }

  isExpanded(maksutietoFormArrayIdx: number): boolean {
    return this.ui.openedMaksutietoIndex === maksutietoFormArrayIdx;
  }

  isShowAddMaksutietoButton() {
    return this.maksutiedot.filter(maksutieto => !!maksutieto.id).length === this.maksutiedotFormArr.value.length;
  }

  paattymisPvmIsUnchanged(idx) {
    const isEdit = this.maksutiedot[this.ui.openedMaksutietoIndex] && this.maksutiedot[this.ui.openedMaksutietoIndex].paattymis_pvm !== undefined;
    if (isEdit) {
      const paattymis_pvm_old = this.maksutiedot[this.ui.openedMaksutietoIndex].paattymis_pvm || '';
      const paattymis_pvm_new = this.vardaDateService.momentToVardaDate(this.maksutiedotFormArr.value[idx].maksutieto_perustiedot.paattymis_pvm) || '';
      return paattymis_pvm_old.localeCompare(paattymis_pvm_new) === 0;
    }
    return false;
  }

  /**
   * This function alters the form template and existing forms if lapsi is yksityinen.
   * Function is called when isLapsiYksityinen is set, and when maksutieto data has been fetched, because we don't know
   * which one finishes first (and both are needed).
   */
  private removeFieldsForYksityinenLapsi() {
    // Only run if isLapsiYksityinen is set and true, and maksutiedotFieldSetTemplate is set as well
    if (this._isLapsiYksityinen !== undefined && this._isLapsiYksityinen && this.maksutiedotFieldSetTemplate) {
      // Alter the template so that new maksutieto forms don't have unnecessary fields
      this.mutateFieldSetForYksityinenLapsi(this.maksutiedotFieldSetTemplate.fieldsets[0]);

      // Alter the existing forms if already created, so that unnecessary fields are removed
      if (Object.keys(this.maksutiedotFieldSetObj).length > 0) {
        for (const [key, fieldSetArray] of Object.entries(this.maksutiedotFieldSetObj)) {
          this.mutateFieldSetForYksityinenLapsi(fieldSetArray[0]);
        }
      }

      this.maksutiedotFormArr.controls
        .map(formGroup => formGroup.get('maksutieto_perustiedot'))
        .forEach((formGroup: FormGroup) => {
          delete formGroup.controls['perheen_koko'];
          delete formGroup.controls['palveluseteli_arvo'];
        });
    }
  }

  private mutateFieldSetForYksityinenLapsi(fieldSet: VardaFieldSet) {
    fieldSet.fields.forEach((field, index) => {
      if (field.key === 'perheen_koko' || field.key === 'palveluseteli_arvo') {
        fieldSet.fields.splice(index, 1);
      }
    });
  }
}
