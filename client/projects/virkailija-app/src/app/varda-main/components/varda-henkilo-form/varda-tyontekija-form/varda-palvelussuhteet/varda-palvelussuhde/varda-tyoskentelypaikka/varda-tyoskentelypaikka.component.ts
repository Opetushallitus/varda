import { Component, OnInit, OnChanges, Input, Inject, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { VardaHenkiloDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess, SaveAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaTyoskentelypaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyoskentelypaikka-dto.model';
import { FormGroup, Validators, FormControl } from '@angular/forms';
import * as moment from 'moment';
import { DOCUMENT } from '@angular/common';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaKoodistoService, VardaDateService } from 'varda-shared';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/models/koodisto-models';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { Moment } from 'moment';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';

@Component({
  selector: 'app-varda-tyoskentelypaikka',
  templateUrl: './varda-tyoskentelypaikka.component.html',
  styleUrls: [
    './varda-tyoskentelypaikka.component.css',
    '../varda-palvelussuhde.component.css',
    '../../../varda-tyontekija-form.component.css',
    '../../../../varda-henkilo-form.component.css'
  ]
})
export class VardaTyoskentelypaikkaComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnChanges, AfterViewInit, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() palvelussuhde: VardaPalvelussuhdeDTO;
  @Input() henkilo: VardaHenkiloDTO;
  @Input() tyoskentelypaikka: VardaTyoskentelypaikkaDTO;
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  toimijaAccess: UserAccess;
  subscriptions: Array<Subscription> = [];
  tehtavanimikkeet: KoodistoDTO;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  isSubmitting = new BehaviorSubject<boolean>(false);
  startDateRange = { min: null, max: null };
  endDateRange = { min: null, max: null };
  koodistoEnum = KoodistoEnum;
  palvelussuhdeFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    @Inject(DOCUMENT) private document,
    private authService: AuthService,
    private henkilostoService: VardaHenkilostoApiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.toimijaAccess = this.authService.getUserAccess();
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.palvelussuhdeFormErrors = this.henkilostoErrorService.initErrorList();
    this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike).subscribe(koodisto => this.tehtavanimikkeet = koodisto);
  }

  ngOnInit() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.tyoskentelypaikka?.id),
      lahdejarjestelma: new FormControl(this.tyoskentelypaikka?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      palvelussuhde: new FormControl(this.palvelussuhde.url),
      toimipaikka_oid: new FormControl(this.tyoskentelypaikka?.toimipaikka_oid || this.henkilonToimipaikka?.organisaatio_oid),
      kiertava_tyontekija_kytkin: new FormControl(this.tyoskentelypaikka?.kiertava_tyontekija_kytkin || false, Validators.required),
      alkamis_pvm: new FormControl(this.tyoskentelypaikka ? moment(this.tyoskentelypaikka?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.tyoskentelypaikka?.paattymis_pvm ? moment(this.tyoskentelypaikka?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      tehtavanimike_koodi: new FormControl(this.tyoskentelypaikka?.tehtavanimike_koodi, Validators.required),
      kelpoisuus_kytkin: new FormControl(this.tyoskentelypaikka?.kelpoisuus_kytkin, Validators.required),
    });

    if (!this.toimipaikkaAccess.tyontekijatiedot.tallentaja || this.tyoskentelypaikka) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.checkFormErrors(this.henkilostoService, 'tyoskentelypaikka', this.tyoskentelypaikka?.id);
    this.initDateFilters();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngAfterViewInit() {
    if (!this.tyoskentelypaikka) {
      this.panelHeader?.focus();
    }

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  ngOnChanges() {
    if (!this.tyoskentelypaikka) {
      this.togglePanel(true, undefined, true);
    }

    if (this.toimipaikkaAccess.tyontekijatiedot.tallentaja) {
      this.toimipaikat = this.authService.getAuthorizedToimipaikat(this.vardaVakajarjestajaService.getFilteredToimipaikat().tallentajaToimipaikat, SaveAccess.tyontekijatiedot);
      this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.organisaatio_oid);
    } else {
      this.toimipaikat = this.vardaVakajarjestajaService.getFilteredToimipaikat().toimipaikat;
    }
  }

  saveTyoskentelypaikka(form: FormGroup): void {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (!form.valid) {
      if (form.controls.kiertava_tyontekija_kytkin.value) {
        form.get('toimipaikka_oid').setValue(null);
      } else if (!form.controls.toimipaikka_oid.value) {
        form.controls.toimipaikka_oid.setErrors({ required: true });
      }

      VardaErrorMessageService.formIsValid(form);
      this.disableSubmit();
    } else {
      const tyoskentelypaikkaJson: VardaTyoskentelypaikkaDTO = {
        ...form.value,
        kiertava_tyontekija_kytkin: form.controls.kiertava_tyontekija_kytkin.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (tyoskentelypaikkaJson.kiertava_tyontekija_kytkin) {
        delete tyoskentelypaikkaJson.toimipaikka_oid;
      }

      if (this.tyoskentelypaikka) {
        this.henkilostoService.updateTyoskentelypaikka(tyoskentelypaikkaJson).subscribe({
          next: () => {
            this.togglePanel(false, true, true);
            this.snackBarService.success(this.i18n.tyoskentelypaikka_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      } else {
        this.henkilostoService.createTyoskentelypaikka(tyoskentelypaikkaJson).subscribe({
          next: () => {
            this.togglePanel(false, true, true);
            this.snackBarService.success(this.i18n.tyoskentelypaikka_save_success);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      }
    }
  }

  deleteTyoskentelypaikka(): void {
    this.henkilostoService.deleteTyoskentelypaikka(this.tyoskentelypaikka.id).subscribe({
      next: () => {
        this.togglePanel(false, true, true);
        this.snackBarService.warning(this.i18n.tyoskentelypaikka_delete_success);
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
    if (this.tyoskentelypaikka) {
      this.formGroup.controls.kiertava_tyontekija_kytkin.disable();
      this.formGroup.controls.toimipaikka_oid.disable();
    }
    if (!this.toimijaAccess.tyontekijatiedot.tallentaja) {
      this.formGroup.controls.kiertava_tyontekija_kytkin.disable();
    }
  }

  initDateFilters() {
    if (this.palvelussuhde) {
      this.startDateRange.min = new Date(this.palvelussuhde.alkamis_pvm);
      this.startDateChange(this.formGroup.controls.alkamis_pvm?.value);

      if (this.palvelussuhde.paattymis_pvm) {
        this.startDateRange.max = new Date(this.palvelussuhde.paattymis_pvm);
        this.endDateRange.max = new Date(this.palvelussuhde.paattymis_pvm);
      }
    }
  }

  startDateChange(startDate: Moment) {
    this.endDateRange.min = startDate?.clone().toDate() || new Date(this.palvelussuhde.alkamis_pvm);
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  sendUpdateList() {
    this.henkilostoService.sendHenkilostoListUpdate();
  }
}
