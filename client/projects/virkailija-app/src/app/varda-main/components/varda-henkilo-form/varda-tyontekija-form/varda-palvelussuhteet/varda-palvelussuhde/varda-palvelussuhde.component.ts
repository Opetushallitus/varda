import { Component, OnInit, OnChanges, Input, Output, EventEmitter, ElementRef, OnDestroy } from '@angular/core';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaTyoskentelypaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyoskentelypaikka-dto.model';
import { VardaPoissaoloDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-poissolo-dto.model';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import * as moment from 'moment';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
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
export class VardaPalvelussuhdeComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnChanges, OnDestroy {
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() palvelussuhde: VardaPalvelussuhdeDTO;
  @Input() henkilonTutkinnot: Array<VardaTutkintoDTO>;
  @Output() changedPalvelussuhde = new EventEmitter<boolean>(true);
  element: ElementRef;
  tyoskentelypaikat: Array<VardaTyoskentelypaikkaDTO>;
  poissaolot: Array<VardaPoissaoloDTO>;
  addTyoskentelypaikkaBoolean: boolean;
  addPoissaoloBoolean: boolean;
  isSubmitting = new BehaviorSubject<boolean>(false);
  palvelussuhdeFormErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  tyosuhdeKoodisto: KoodistoDTO;
  tyoaikaKoodisto: KoodistoDTO;
  minEndDate: Date;
  koodistoEnum = KoodistoEnum;
  private henkilostoErrorService: VardaErrorMessageService;

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
  }

  ngOnInit() {
    const oletustutkinto = this.henkilonTutkinnot.length === 1 ? this.henkilonTutkinnot[0].tutkinto_koodi : null;
    this.formGroup = new FormGroup({
      id: new FormControl(this.palvelussuhde?.id),
      lahdejarjestelma: new FormControl(this.palvelussuhde?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      tyontekija: new FormControl(this.palvelussuhde?.tyontekija || `/api/henkilosto/v1/tyontekijat/${this.tyontekija.id}/`),
      toimipaikka_oid: new FormControl(this.palvelussuhde ? null : this.henkilonToimipaikka?.organisaatio_oid),
      alkamis_pvm: new FormControl(this.palvelussuhde ? moment(this.palvelussuhde?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.palvelussuhde?.paattymis_pvm ? moment(this.palvelussuhde?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      tyoaika_koodi: new FormControl(this.palvelussuhde?.tyoaika_koodi, Validators.required),
      tyosuhde_koodi: new FormControl(this.palvelussuhde?.tyosuhde_koodi, Validators.required),
      tyoaika_viikossa: new FormControl(this.palvelussuhde?.tyoaika_viikossa, [Validators.pattern('^\\d+([,.]\\d{1,2})?$'), Validators.max(50), Validators.required]),
      tutkinto_koodi: new FormControl(this.palvelussuhde?.tutkinto_koodi || oletustutkinto, Validators.required),
    });

    if (!this.toimipaikkaAccess.tyontekijatiedot.tallentaja || this.palvelussuhde) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.checkFormErrors(this.henkilostoService, 'palvelussuhde', this.palvelussuhde?.id);
    this.initDateFilters();

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngOnChanges() {
    if (this.palvelussuhde) {
      this.getTyoskentelypaikat();
      this.getPoissaolot();
    } else {
      this.togglePanel(true, undefined, true);
    }
  }

  savePalvelussuhde(form: FormGroup): void {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const palvelussuhdeDTO: VardaPalvelussuhdeDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (this.palvelussuhde) {
        this.henkilostoService.updatePalvelussuhde(palvelussuhdeDTO).subscribe({
          next: palvelussuhdeData => {
            this.changedPalvelussuhde.emit();
            this.snackBarService.success(this.i18n.palvelussuhde_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      } else {
        this.henkilostoService.createPalvelussuhde(palvelussuhdeDTO).subscribe({
          next: palvelussuhdeData => {
            this.togglePanel(false, true, true);
            this.snackBarService.success(this.i18n.palvelussuhde_save_success);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      }

    } else {
      this.disableSubmit();
    }
  }

  closePoissaolo(refresh?: boolean, hideAddPoissaolo?: boolean): void {
    if (hideAddPoissaolo) {
      this.addPoissaoloBoolean = false;
    }

    if (refresh) {
      this.getPoissaolot();
    }
  }

  getPoissaolot(): void {
    this.henkilostoService.getPoissaolot(this.palvelussuhde.id).subscribe({
      next: poissaoloData => this.poissaolot = poissaoloData,
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  deletePalvelussuhde(): void {
    this.henkilostoService.deletePalvelussuhde(this.palvelussuhde.id).subscribe({
      next: deleted => {
        this.togglePanel(false, true, true);
        this.snackBarService.warning(this.i18n.palvelussuhde_delete_success);
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  getTyoskentelypaikat(): void {
    this.henkilostoService.getTyoskentelypaikat(this.palvelussuhde.id).subscribe({
      next: tyoskentelypaikkaData => {
        this.tyoskentelypaikat = tyoskentelypaikkaData;
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  closeTyoskentelypaikka(refresh?: boolean, hideAddTyoskentelypaikka?: boolean): void {
    if (hideAddTyoskentelypaikka) {
      this.addTyoskentelypaikkaBoolean = false;
    }

    if (refresh) {
      this.getTyoskentelypaikat();
    }
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
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

  sendUpdateList() {
    this.henkilostoService.sendHenkilostoListUpdate();
  }
}
