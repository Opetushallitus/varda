import { Component, OnInit, Input, Output, EventEmitter, ElementRef, OnDestroy } from '@angular/core';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import * as moment from 'moment';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { finalize, Observable, Subscription } from 'rxjs';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaKoodistoService, VardaDateService } from 'varda-shared';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/models/koodisto-models';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { Moment } from 'moment';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import {
  TyontekijaPalvelussuhde, TyontekijaPidempiPoissaolo,
  TyontekijaTutkinto, TyontekijaTyoskentelypaikka
} from '../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { sortByAlkamisPvm } from '../../../../../../utilities/helper-functions';
import { VardaPalvelussuhdeDTO } from '../../../../../../utilities/models/dto/varda-tyontekija-dto.model';

@Component({
  selector: 'app-varda-palvelussuhde',
  templateUrl: './varda-palvelussuhde.component.html',
  styleUrls: [
    './varda-palvelussuhde.component.css',
    '../varda-palvelussuhteet.component.css',
    '../../varda-tyontekija-form.component.css',
    '../../../varda-henkilo-form.component.css'
  ]
})
export class VardaPalvelussuhdeComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnDestroy {
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() palvelussuhde: TyontekijaPalvelussuhde;
  @Output() addObject = new EventEmitter<TyontekijaPalvelussuhde>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  element: ElementRef;
  addTyoskentelypaikkaBoolean: boolean;
  addPoissaoloBoolean: boolean;
  isSubmitting = false;
  palvelussuhdeFormErrors: Observable<Array<ErrorTree>>;
  tyosuhdeKoodisto: KoodistoDTO;
  tyoaikaKoodisto: KoodistoDTO;
  tutkintoList: Array<TyontekijaTutkinto> = [];
  minEndDate: Date;
  koodistoEnum = KoodistoEnum;
  tyontekijaId: number;
  tyoskentelypaikkaList: Array<TyontekijaTyoskentelypaikka> = [];
  pidempiPoissaoloList: Array<TyontekijaPidempiPoissaolo> = [];

  private henkilostoErrorService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private el: ElementRef,
    private henkilostoService: VardaHenkilostoApiService,
    private koodistoService: VardaKoodistoService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.element = this.el;
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.palvelussuhdeFormErrors = this.henkilostoErrorService.initErrorList();

    this.koodistoService.getKoodisto(KoodistoEnum.tyosuhde).subscribe(koodisto => this.tyosuhdeKoodisto = koodisto);
    this.koodistoService.getKoodisto(KoodistoEnum.tyoaika).subscribe(koodisto => this.tyoaikaKoodisto = koodisto);

    this.tyontekijaId = this.henkilostoService.activeTyontekija.getValue().id;
  }

  ngOnInit() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.palvelussuhde?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      tyontekija: new FormControl(this.henkilostoService.getTyontekijaUrl(this.tyontekijaId)),
      toimipaikka_oid: new FormControl(this.palvelussuhde ? null : this.henkilonToimipaikka?.organisaatio_oid),
      alkamis_pvm: new FormControl(this.palvelussuhde ? moment(this.palvelussuhde?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.palvelussuhde?.paattymis_pvm ? moment(this.palvelussuhde?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      tyoaika_koodi: new FormControl(this.palvelussuhde?.tyoaika_koodi, Validators.required),
      tyosuhde_koodi: new FormControl(this.palvelussuhde?.tyosuhde_koodi, Validators.required),
      tyoaika_viikossa: new FormControl(this.palvelussuhde?.tyoaika_viikossa, [Validators.pattern('^\\d+([,.]\\d{1,2})?$'), Validators.max(50), Validators.required]),
      tutkinto_koodi: new FormControl(this.palvelussuhde?.tutkinto_koodi || null, Validators.required),
    });

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true)),
      this.henkilostoService.tutkintoChanged.subscribe(() => {
        this.tutkintoList = this.henkilostoService.activeTyontekija.getValue().tutkinnot;
        if (this.tutkintoList.length === 1) {
          this.formGroup.controls.tutkinto_koodi.setValue(this.tutkintoList[0].tutkinto_koodi);
        }
      })
    );

    if (this.palvelussuhde) {
      this.disableForm();
      this.tyoskentelypaikkaList = this.palvelussuhde.tyoskentelypaikat.sort(sortByAlkamisPvm);
      this.pidempiPoissaoloList = this.palvelussuhde.pidemmatpoissaolot.sort(sortByAlkamisPvm);
    } else {
      this.enableForm();
      this.togglePanel(true);
    }

    this.checkFormErrors(this.henkilostoService, 'palvelussuhde', this.palvelussuhde?.id);
    this.initDateFilters();
  }

  savePalvelussuhde(form: FormGroup): void {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const palvelussuhdeDTO: VardaPalvelussuhdeDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      const observable = this.palvelussuhde ? this.henkilostoService.updatePalvelussuhde(palvelussuhdeDTO) :
        this.henkilostoService.createPalvelussuhde(palvelussuhdeDTO);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.palvelussuhde) {
              // Close panel if object was created
              this.togglePanel(false);
            }

            this.snackBarService.success(this.i18n.palvelussuhde_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();
            this.palvelussuhde = {...result, tyoskentelypaikat: this.tyoskentelypaikkaList,
              pidemmatpoissaolot: this.pidempiPoissaoloList};
            this.addObject.emit(this.palvelussuhde);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deletePalvelussuhde(): void {
    this.subscriptions.push(
      this.henkilostoService.deletePalvelussuhde(this.palvelussuhde.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.palvelussuhde_delete_success);
          this.henkilostoService.sendHenkilostoListUpdate();
          this.deleteObject.emit(this.palvelussuhde.id);
        },
        error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
      })
    );
  }

  addTyoskentelypaikka(tyoskentelypaikka: TyontekijaTyoskentelypaikka) {
    this.tyoskentelypaikkaList = this.tyoskentelypaikkaList.filter(obj => obj.id !== tyoskentelypaikka.id);
    this.tyoskentelypaikkaList.push(tyoskentelypaikka);
    this.tyoskentelypaikkaList = this.tyoskentelypaikkaList.sort(sortByAlkamisPvm);
    this.updateActiveTyontekija();
    this.henkilostoService.tyoskentelypaikkaChanged.next(true);
  }

  deleteTyoskentelypaikka(objectId: number) {
    this.tyoskentelypaikkaList = this.tyoskentelypaikkaList.filter(obj => obj.id !== objectId);
    this.updateActiveTyontekija();
  }

  addPidempiPoissaolo(pidempiPoissaolo: TyontekijaPidempiPoissaolo) {
    this.pidempiPoissaoloList = this.pidempiPoissaoloList.filter(obj => obj.id !== pidempiPoissaolo.id);
    this.pidempiPoissaoloList.push(pidempiPoissaolo);
    this.pidempiPoissaoloList = this.pidempiPoissaoloList.sort(sortByAlkamisPvm);
    this.updateActiveTyontekija();
  }

  deletePidempiPoissaolo(objectId: number) {
    this.pidempiPoissaoloList = this.pidempiPoissaoloList.filter(obj => obj.id !== objectId);
    this.updateActiveTyontekija();
  }

  updateActiveTyontekija() {
    const activeTyontekija = this.henkilostoService.activeTyontekija.getValue();
    const activePalvelussuhde = activeTyontekija.palvelussuhteet.find(obj => obj.id === this.palvelussuhde.id);
    activePalvelussuhde.tyoskentelypaikat = this.tyoskentelypaikkaList;
    activePalvelussuhde.pidemmatpoissaolot = this.pidempiPoissaoloList;
    this.henkilostoService.activeTyontekija.next(activeTyontekija);
  }

  hideAddPidempiPoissaolo(): void {
    this.addPoissaoloBoolean = false;
  }

  hideAddTyoskentelypaikka(): void {
    this.addTyoskentelypaikkaBoolean = false;
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 500);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
  }

  initDateFilters() {
    if (this.palvelussuhde?.alkamis_pvm) {
      this.minEndDate = new Date(this.palvelussuhde.alkamis_pvm);
    }
  }

  startDateChange(startDate: Moment) {
    this.minEndDate = startDate?.clone().toDate();
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
}
