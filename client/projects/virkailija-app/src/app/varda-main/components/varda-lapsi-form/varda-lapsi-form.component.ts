import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  QueryList,
  SimpleChanges,
  ViewChildren,
  ViewChild
} from '@angular/core';
import { FormArray, FormControl, FormGroup, Validators } from '@angular/forms';
import {
  VardaEntityNames,
  VardaFieldSet,
  VardaHenkiloDTO,
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
import { forkJoin, Observable, BehaviorSubject } from 'rxjs';
import { VardaDateService } from '../../services/varda-date.service';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { UserAccess, SaveAccess } from '../../../utilities/models/varda-user-access.model';
import { VardaLapsiCreateDto, LapsiListDTO } from '../../../utilities/models/dto/varda-lapsi-dto.model';
import { MatRadioChange } from '@angular/material/radio';
import { MatExpansionPanel } from '@angular/material/expansion';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { ErrorTree, HenkilostoErrorMessageService } from '../../../core/services/varda-henkilosto-error-message.service';
import { VardaLapsiService } from '../../../core/services/varda-lapsi.service';
import { VardaModalService } from '../../../core/services/varda-modal.service';

declare var $: any;

@Component({
  selector: 'app-varda-lapsi-form',
  templateUrl: './varda-lapsi-form.component.html',
  styleUrls: ['./varda-lapsi-form.component.css']
})
export class VardaLapsiFormComponent implements OnInit, OnChanges, AfterViewInit {
  @Input() henkilo: VardaHenkiloDTO;
  @Input() lapsi: LapsiListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() isEdit: boolean;
  @Output() saveLapsiSuccess: EventEmitter<any> = new EventEmitter();
  @Output() saveLapsiFailure: EventEmitter<any> = new EventEmitter();
  @Output() updateLapsi: EventEmitter<any> = new EventEmitter();
  @Output() deleteLapsi: EventEmitter<any> = new EventEmitter();
  @Output() valuesChanged: EventEmitter<any> = new EventEmitter();
  @ViewChild('backendErrorContainer') backendErrorContainer: ElementRef;
  @ViewChildren('varhaiskasvatuspaatosPanels') varhaiskasvatuspaatosPanels: QueryList<MatExpansionPanel>;
  @ViewChildren('varhaiskasvatuspaatosPanels', { read: ElementRef }) varhaiskasvatuspaatosPanelRefs: QueryList<ElementRef>;
  @ViewChildren('varhaiskasvatussuhdePanels') varhaiskasvatussuhdePanels: QueryList<MatExpansionPanel>;
  @ViewChildren('varhaiskasvatussuhdePanels', { read: ElementRef }) varhaiskasvatussuhdePanelRefs: QueryList<ElementRef>;

  currentLapsi: VardaLapsiDTO;
  promptDeleteHenkilo = false;

  isCurrentLapsiYksityinen: boolean;
  i18n = VirkailijaTranslations;
  lapsiForm: FormGroup;
  lapsiCreateForm: FormGroup;
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

  allToimipaikkaOptions: Array<VardaToimipaikkaDTO>;
  tallentajaToimipaikkaOptions: Array<VardaToimipaikkaDTO>;
  varhaiskasvatussuhteet: Array<VardaVarhaiskasvatussuhdeDTO>;
  varhaiskasvatuspaatokset: Array<VardaVarhaiskasvatuspaatosDTO>;

  selectedToimipaikka: VardaToimipaikkaDTO;

  lapsiFormErrors: Array<any>;
  deleteLapsiErrors: Observable<Array<ErrorTree>>;
  private deleteLapsiErrorService = new HenkilostoErrorMessageService();
  hideMaksutiedot: boolean;
  varhaiskasvatuspaatoksetFormChanged: boolean;
  varhaiskasvatussuhteetFormChanged: boolean;
  toimipaikkaAccess: UserAccess;
  paosJarjestajaKunnat$ = new BehaviorSubject<Array<VardaVakajarjestajaUi>>(undefined);

  /**
   * Map that is used to link vakasuhteet to vakapaatokset. Vakasuhde forms are displayed inside vakapaatos based
   * on this map.
   * key=vakapaatos index
   * value=list of vakasuhde indexes
   */
  vakasuhteetVakapaatoksetMap: { [key: number]: Array<number> } = {};

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
    private lapsiService: VardaLapsiService,
    private modalService: VardaModalService,
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
    };

    this.deleteLapsiErrors = this.deleteLapsiErrorService.initErrorList();
  }

  private fetchPaosJarjestajas() {
    const vakajarjestajaId = this.vardaVakajarjestajaService.selectedVakajarjestaja.id;
    const toimipaikkaId = this.selectedToimipaikka.id;
    this.vardaApiWrapperService.getPaosJarjestajat(vakajarjestajaId, toimipaikkaId)
      .subscribe({
        next: (data) => this.paosJarjestajaKunnat$.next(data),
        error: e => console.error('Could not fetch paos-jarjestajat', e),
      });
  }

  addNewRecurringStructure(entityName: string, vakapaatosIndex?: number): void {
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
      fg.addControl('varhaiskasvatuspaatos', new FormControl(this.varhaiskasvatuspaatokset[vakapaatosIndex]));
      fg.addControl('toimipaikka', new FormControl(this.selectedToimipaikka?.nimi ? this.selectedToimipaikka : '', [Validators.required]));
    }

    formArr.push(fg);
    const newIndex = formArr.length - 1;
    fieldSets[newIndex] = fieldSetCopy;

    setTimeout(() => {
      panels = panels.toArray();
      if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
        // If we're adding vakasuhde, the panel may not hierarchically be the last one, so find the panel based on
        // data-realindex -attribute.
        const panelIndex = this.varhaiskasvatussuhdePanelRefs.toArray().findIndex(elementRef => {
          const realIndex = elementRef.nativeElement.getAttribute('data-realindex');
          if (realIndex === String(newIndex)) {
            return true;
          }
        });
        panelToOpen = panels[panelIndex];
      } else {
        // When adding vakapaatos, the panel is always the last one.
        panelToOpen = panels[newIndex];
      }
      if (panelToOpen) {
        panelToOpen.open();
      }
    });

    setTimeout(() => {
      this.setRecurringStructureFocus(entityName, newIndex);
    }, 500);

    if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      this.updateVakasuhteetVakapaatosMap();
    }
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

        this.ui.lapsiFormSaveSuccess = true;
        this.updateVakasuhteetVakapaatosMap();
      }, this.onSaveError.bind(this, formArrIndex, entity));
    } else {
      formArr.removeAt(formArrIndex);

      this.updateVakasuhteetVakapaatosMap();
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
    this.vardaApiWrapperService.deleteLapsi(lapsiId).subscribe({
      next: () => {
        this.ui.lapsiFormSaveSuccess = true;

        this.lapsiService.sendLapsiListUpdate();
        this.modalService.setModalOpen(false);
      }, error: err => this.deleteLapsiErrorService.handleError(err)
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
    } else {
      const tsKey = entityStr === VardaEntityNames.VARHAISKASVATUSPAATOS ? 'label.add-new-varhaiskasvatuspaatos' : 'label.add-new-varhaiskasvatussuhde';
      this.translateService.get(tsKey).subscribe(st => rv = st);
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

  createLapsiDTO(henkilo: VardaHenkiloDTO): VardaLapsiCreateDto {
    const lapsiDTO = new VardaLapsiCreateDto(this.lapsiCreateForm.value);
    lapsiDTO.henkilo = henkilo.url;
    return lapsiDTO;
  }

  setPaosOrganisaatiot(event) {
    const omaOrganisaatioUrl = event.target.value;
    if (omaOrganisaatioUrl) {
      let paosOrganisaatioUrl = VardaApiService.getVakajarjestajaUrlFromId(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id);
      // Comparing between relative and absolute path
      if (omaOrganisaatioUrl && omaOrganisaatioUrl.endsWith(paosOrganisaatioUrl)) {
        paosOrganisaatioUrl = this.vardaVakajarjestajaService.getSelectedToimipaikka().paos_organisaatio_url;
      }
      this.lapsiCreateForm.get('vakatoimija').setValue(null);
      this.lapsiCreateForm.get('paos_organisaatio').setValue(paosOrganisaatioUrl);
      this.lapsiCreateForm.get('oma_organisaatio').setValue(omaOrganisaatioUrl);
    } else {
      this.clearPaosOrganisaatiot();
    }
  }

  getLapsiFormData(): any {
    const data = {
      createLapsiDto: this.createLapsiDTO(this.henkilo),
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
      const vakajarjestajaToimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat();
      this.allToimipaikkaOptions = vakajarjestajaToimipaikat.allToimipaikat;

      if (this.toimipaikkaAccess.lapsitiedot.tallentaja) {
        this.tallentajaToimipaikkaOptions = this.authService.getAuthorizedToimipaikat(vakajarjestajaToimipaikat.tallentajaToimipaikat, SaveAccess.lapsitiedot);
      } else {
        this.tallentajaToimipaikkaOptions = vakajarjestajaToimipaikat.allToimipaikat;
      }
      this.toimipaikkaForm = new FormGroup({ toimipaikka: new FormControl(this.selectedToimipaikka) });
      this.selectedSuhdeForm = new FormGroup({ addVarhaiskasvatussuhde: new FormControl() });
      this.setToimipaikka();

      data = this.filterJarjestamismuodot(data);
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

      this.updateVakasuhteetVakapaatosMap();
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
    return this.allToimipaikkaOptions.find((toimipaikkaObj) => toimipaikkaObj.url === suhde.toimipaikka);
  }

  getVarhaiskasvatuspaatosByUrl(varhaiskasvatussuhde: VardaVarhaiskasvatussuhdeDTO): VardaVarhaiskasvatuspaatosDTO {
    return this.varhaiskasvatuspaatokset
      .find((varhaiskasvatuspaatosObj) => varhaiskasvatuspaatosObj.url === varhaiskasvatussuhde.varhaiskasvatuspaatos);
  }

  initExistingLapsiFormData(lapsiReference: string): Observable<any> {
    return new Observable((observer) => {
      return this.vardaApiWrapperService.getEntityReferenceByEndpoint(lapsiReference).subscribe((lapsi) => {
        this.currentLapsi = lapsi;
        this.maksutietoToimijaTallentajalle(lapsi);
        const lapsiId = this.vardaUtilityService.parseIdFromUrl(lapsi.url);
        this.ui.isPerustiedotLoading = false;
        this.vardaApiWrapperService.getVarhaiskasvatussuhteetByLapsi(lapsiId).subscribe((vakasuhteet) => {
          this.vardaApiWrapperService.getVarhaiskasvatuspaatoksetByLapsi(lapsiId)
            .subscribe((vakapaatokset) => {
              this.varhaiskasvatussuhteet = [];
              const tempVarhaiskasvatussuhteet = [...vakasuhteet];

              this.varhaiskasvatuspaatokset = [...vakapaatokset];

              this.varhaiskasvatuspaatokset.sort(this.sortRecurringEntityListsByDates.bind(this));
              if (this.varhaiskasvatuspaatokset.length) {
                this.isCurrentLapsiYksityinen = ['jm04', 'jm05'].includes(this.varhaiskasvatuspaatokset[0].jarjestamismuoto_koodi.toLowerCase());
              }

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
              this.checkHidingMaksutiedot();
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

  saveRecurringStructure(formArrIndex: number, entityName: string, panel: MatExpansionPanel): void {
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
      next: this.onSaveSuccess.bind(this, entityName, formArrIndex, isEdit, panel),
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

    if (this.paosJarjestajaKunnat$.getValue() !== undefined) {
      rv = rv && this.lapsiCreateForm.valid;
    }

    if (!this.selectedToimipaikka) {
      rv = false;
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
          this.lapsiService.sendLapsiListUpdate();
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
      const panel = args[3];
      const entity = args[4];

      let entities, formArray;
      if (action === VardaEntityNames.VARHAISKASVATUSPAATOS) {
        this.updateLapsi.emit({ saveVarhaiskasvatuspaatos: { url: this.currentLapsi.url, entity: entity } });
        this.lapsiService.sendLapsiListUpdate();
        entities = this.varhaiskasvatuspaatokset;
        formArray = <FormArray>this.varhaiskasvatuspaatoksetForm.get('varhaiskasvatuspaatoksetFormArr');
      } else if (action === VardaEntityNames.VARHAISKASVATUSSUHDE) {
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

      if (panel) {
        panel.close();
      }

      const newIndex = entities.findIndex((r) => {
        return r.url === entity.url;
      });

      const entityToBeMoved = formArray.at(formArrIndex);
      formArray.removeAt(formArrIndex);
      formArray.insert(newIndex, entityToBeMoved);

      this.updateVakasuhteetVakapaatosMap();

      setTimeout(() => {
        this.setControlsDisabledOnEdit(action, entityToBeMoved);
        this.setFormsChangedState(action, false);
        this.checkIfAnyOfTheFormsHasChanged();
        this.setRecurringStructureFocus(action, newIndex);
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
    let panelRefs, panelToFocus;
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      panelRefs = this.varhaiskasvatuspaatosPanelRefs;
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      panelRefs = this.varhaiskasvatussuhdePanelRefs;
    }

    if (!isNaN(index)) {
      panelToFocus = panelRefs.find(element => {
        const identifier = element.nativeElement.getAttribute('data-realindex');
        if (identifier === String(index)) {
          return true;
        }
      });
    } else {
      panelToFocus = panelRefs[panelRefs.length - 1];
    }
    panelToFocus = panelToFocus.nativeElement;

    const headerElement = panelToFocus.children[0];
    headerElement.focus();
    panelToFocus.scrollIntoView({ behavior: 'smooth' });
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
    this.ui.lapsiFormHasErrors = true;
    this.ui.isSubmitting = false;
    this.hideMessages();
    this.backendErrorContainer.nativeElement.scrollIntoView({ behavior: 'smooth' });
  }

  onExpansionPanelClick($event: any, index: number, entityName: string, panel: MatExpansionPanel): void {
    const entity = this.getExistingEntityByIndex(index, entityName);
    this.ui.lapsiFormSaveSuccess = false;
    if (entityName === VardaEntityNames.VARHAISKASVATUSPAATOS) {
      this.ui.openedVarhaiskasvatuspaatosIndex = index;
      this.preventClosingForUnsavedEntity($event, entity, panel);
    } else if (entityName === VardaEntityNames.VARHAISKASVATUSSUHDE) {
      this.ui.openedVarhaiskasvatussuhdeIndex = index;
      this.preventClosingForUnsavedEntity($event, entity, panel);
    }
  }

  preventClosingForUnsavedEntity($event: Event, entity: any, panel: MatExpansionPanel) {
    if (!entity) {
      $event.stopPropagation();
      panel.open();
    }
  }

  ngOnChanges(changes: SimpleChanges) {

    if (changes.henkilonToimipaikka) {
      this.selectedToimipaikka = changes.henkilonToimipaikka.currentValue;
    }

    if (changes.isEdit && changes.lapsi) {
      this.currentLapsi = null;

      if (changes.isEdit.currentValue) {
        this.ui.saveBtnText = 'label.generic-update';

        forkJoin([
          this.initExistingLapsiFormData(this.lapsi.url),
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
        this.paosJarjestajaKunnat$.subscribe(kunnat => {
          this.initLapsiFormFields();
        });
      }
    } else if (changes.henkilo && changes.henkilo.currentValue) {
      this.initLapsiFormFields();
    }
  }

  ngOnInit() {
    this.toimipaikkaAccess = this.authService.getUserAccess(this.henkilonToimipaikka?.organisaatio_oid);
    this.ui.isPerustiedotLoading = true;
    this.lapsiForm = new FormGroup({});
    this.varhaiskasvatussuhteetForm = new FormGroup({});
    this.varhaiskasvatussuhdeForm = new FormGroup({});
    this.varhaiskasvatuspaatoksetForm = new FormGroup({});
    this.varhaiskasvatuspaatosForm = new FormGroup({});
    this.lapsiCreateForm = new FormGroup({
      henkilo: new FormControl(new VardaHenkiloDTO()),
      vakatoimija: new FormControl(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().url),
      oma_organisaatio: new FormControl(null, [Validators.required]),
      paos_organisaatio: new FormControl(null, [Validators.required]),
    });
  }

  fetchPaosOrganisaatiot(event: MatRadioChange) {
    const isPaos = event.value;
    if (isPaos) {
      this.fetchPaosJarjestajas();
    } else {
      this.paosJarjestajaKunnat$.next(undefined);
      this.clearPaosOrganisaatiot();
    }
  }



  clearPaosOrganisaatiot() {
    this.lapsiCreateForm.get('vakatoimija').setValue(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().url);
    this.lapsiCreateForm.get('paos_organisaatio').setValue(null);
    this.lapsiCreateForm.get('oma_organisaatio').setValue(null);
  }

  filterJarjestamismuodot(fieldsetGroup: any): any {
    if (fieldsetGroup[1].fieldsets[1].fields[0].key !== 'jarjestamismuoto_koodi') {
      console.error('vakapaatos.json has been edited, järjestamismuoto_koodi not found');
    }

    if (this.vardaVakajarjestajaService.selectedVakajarjestaja.kunnallinen_kytkin) { // kunta ei voi tallentaa jm04/05
      fieldsetGroup[1].fieldsets[1].fields[0].options = fieldsetGroup[1].fieldsets[1].fields[0].options.filter(option => !['jm04', 'jm05'].includes(option.code));
    } else { // yksityinen ei voi tallentaa jm01
      fieldsetGroup[1].fieldsets[1].fields[0].options = fieldsetGroup[1].fieldsets[1].fields[0].options.filter(option => option.code !== 'jm01');
    }

    if (this.paosJarjestajaKunnat$.getValue() || this.currentLapsi?.paos_organisaatio_oid) { // paos-kytkin tarjoaa pelkkää JM02/03
      fieldsetGroup[1].fieldsets[1].fields[0].options = fieldsetGroup[1].fieldsets[1].fields[0].options.filter(option => ['jm02', 'jm03'].includes(option.code));
    } else if ((!this.currentLapsi && !this.paosJarjestajaKunnat$.getValue()) || !this.selectedToimipaikka?.paos_organisaatio_url) {
      // poistetaan eipaoskytkin uudelta lapselta jm02/03 tai jos selectedToimipaikka EI paostoimipaikka
      fieldsetGroup[1].fieldsets[1].fields[0].options = fieldsetGroup[1].fieldsets[1].fields[0].options.filter(option => !['jm02', 'jm03'].includes(option.code));
    }
    return fieldsetGroup;
  }

  checkHidingMaksutiedot(): void {
    const excludedJarjestamismuodot = ['jm02', 'jm03'];
    const isYksityinen = !this.vardaVakajarjestajaService.selectedVakajarjestaja.kunnallinen_kytkin;
    const hasJM23 = this.varhaiskasvatuspaatokset?.some(vakapaatos => excludedJarjestamismuodot.includes(vakapaatos.jarjestamismuoto_koodi));
    const isNotMyPAOSLapsi = (this.currentLapsi?.oma_organisaatio_oid && this.currentLapsi.oma_organisaatio_oid !== this.vardaVakajarjestajaService.selectedVakajarjestaja.organisaatio_oid);
    this.hideMaksutiedot = isNotMyPAOSLapsi || (isYksityinen && hasJM23 && !!this.currentLapsi?.paos_organisaatio_oid);
  }

  maksutietoToimijaTallentajalle(lapsi: VardaLapsiDTO): void {
    if (!this.toimipaikkaAccess.huoltajatiedot.tallentaja &&
      (!lapsi.oma_organisaatio || lapsi.oma_organisaatio_oid === this.vardaVakajarjestajaService.selectedVakajarjestaja.organisaatio_oid)) {
      const toimijaAccess = this.authService.getUserAccess();
      this.toimipaikkaAccess.huoltajatiedot.tallentaja = toimijaAccess.huoltajatiedot.tallentaja;
      this.toimipaikkaAccess.huoltajatiedot.katselija = this.toimipaikkaAccess.huoltajatiedot.katselija || toimijaAccess.huoltajatiedot.tallentaja;
    }
  }

  isVakapaatosWithoutVakasuhde(vakapaatosIndex: number): boolean {
    if (!this.varhaiskasvatuspaatokset[vakapaatosIndex]) {
      return false;
    }

    const vakasuhdeList = this.vakasuhteetVakapaatoksetMap[vakapaatosIndex];
    return !vakasuhdeList || !vakasuhdeList.length;
  }

  private updateVakasuhteetVakapaatosMap(): void {
    this.vakasuhteetVakapaatoksetMap = {};
    const vakasuhdeControls = this.varhaiskasvatussuhteetForm.get('varhaiskasvatussuhteetFormArr')['controls'];
    vakasuhdeControls.forEach((formGroup: FormGroup, vakasuhdeIndex: number) => {
      const vakapaatosIndex = this.varhaiskasvatuspaatokset.findIndex(vakapaatos => {
        return formGroup.get('varhaiskasvatuspaatos').value.id === vakapaatos.id;
      });

      if (!this.vakasuhteetVakapaatoksetMap[vakapaatosIndex]) {
        this.vakasuhteetVakapaatoksetMap[vakapaatosIndex] = [vakasuhdeIndex];
      } else {
        this.vakasuhteetVakapaatoksetMap[vakapaatosIndex].push(vakasuhdeIndex);
      }
    });
  }
}
