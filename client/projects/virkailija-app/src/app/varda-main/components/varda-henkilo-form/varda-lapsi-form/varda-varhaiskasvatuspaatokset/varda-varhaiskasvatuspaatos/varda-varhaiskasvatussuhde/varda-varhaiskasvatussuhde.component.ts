import { Component, OnInit, OnChanges, Input, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import * as moment from 'moment';
import { Moment } from 'moment';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVarhaiskasvatuspaatosDTO, VardaVarhaiskasvatussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { UserAccess, SaveAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaDateService } from 'projects/virkailija-app/src/app/varda-main/services/varda-date.service';
import { Subscription, Observable, BehaviorSubject } from 'rxjs';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { KoodistoDTO, VardaKoodistoService, KoodistoEnum } from 'varda-shared';
import { TranslateService } from '@ngx-translate/core';
import { VardaHenkiloFormAccordionAbstractComponent } from '../../../../varda-henkilo-form-accordion/varda-henkilo-form-accordion.abstract';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';

@Component({
  selector: 'app-varda-varhaiskasvatussuhde',
  templateUrl: './varda-varhaiskasvatussuhde.component.html',
  styleUrls: [
    './varda-varhaiskasvatussuhde.component.css',
    '../varda-varhaiskasvatuspaatos.component.css',
    '../../varda-varhaiskasvatuspaatokset.component.css',
    '../../../varda-lapsi-form.component.css',
    '../../../../varda-henkilo-form.component.css'
  ]
})
export class VardaVarhaiskasvatussuhdeComponent extends VardaHenkiloFormAccordionAbstractComponent implements OnInit, OnChanges, AfterViewInit, OnDestroy {
  @Input() lapsitiedotTallentaja: boolean;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() varhaiskasvatuspaatos: VardaVarhaiskasvatuspaatosDTO;
  @Input() lapsi: LapsiListDTO;
  @Input() varhaiskasvatussuhde: VardaVarhaiskasvatussuhdeDTO;
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  toimijaAccess: UserAccess;
  formGroup: FormGroup;
  subscriptions: Array<Subscription> = [];
  tehtavanimikkeet: KoodistoDTO;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  isSubmitting = new BehaviorSubject<boolean>(false);
  startDateRange = { min: null, max: null };
  endDateRange = { min: null, max: null };

  varhaiskasvatussuhdeFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private authService: AuthService,
    private lapsiService: VardaLapsiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.toimijaAccess = this.authService.getUserAccess();
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.varhaiskasvatussuhdeFormErrors = this.henkilostoErrorService.initErrorList();
    this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike).subscribe(koodisto => this.tehtavanimikkeet = koodisto);
    this.initToimipaikat();
  }

  ngOnInit() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.varhaiskasvatussuhde?.id),
      lahdejarjestelma: new FormControl(this.varhaiskasvatussuhde?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      varhaiskasvatuspaatos: new FormControl(this.varhaiskasvatuspaatos.url, Validators.required),
      alkamis_pvm: new FormControl(this.varhaiskasvatussuhde ? moment(this.varhaiskasvatussuhde?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(
        this.varhaiskasvatussuhde?.paattymis_pvm ? moment(this.varhaiskasvatussuhde?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null,
        this.varhaiskasvatuspaatos.paattymis_pvm ? [Validators.required] : null),
      toimipaikka: new FormControl(this.varhaiskasvatussuhde?.toimipaikka || this.henkilonToimipaikka?.url, Validators.required),
    });

    if (!this.lapsitiedotTallentaja || this.varhaiskasvatussuhde) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.checkFormErrors(this.lapsiService, 'vakasuhde', this.varhaiskasvatussuhde?.id);

    this.initDateFilters();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngAfterViewInit() {
    if (!this.varhaiskasvatussuhde) {
      this.panelHeader?.focus();
    }

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  ngOnChanges() {
    if (!this.varhaiskasvatussuhde) {
      this.togglePanel(true, undefined, true);
    }

    const filteredToimipaikat = this.vardaVakajarjestajaService.getFilteredToimipaikat();
    if (this.lapsitiedotTallentaja) {
      this.toimipaikat = this.authService.getAuthorizedToimipaikat(filteredToimipaikat.tallentajaToimipaikat, SaveAccess.lapsitiedot);
      this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.organisaatio_oid);
      // remove PAOS-toimipaikat from JM01
      if (this.varhaiskasvatuspaatos.jarjestamismuoto_koodi.toLocaleUpperCase() === 'JM01') {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => !toimipaikka.paos_organisaatio_url);
      }
    } else {
      this.toimipaikat = filteredToimipaikat.toimipaikat;
    }

    if (this.lapsi?.tallentaja_organisaatio_oid) {
      const vakajarjestajaOID = this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid;
      if (this.lapsi.paos_organisaatio_oid === vakajarjestajaOID) {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => !toimipaikka.paos_organisaatio_url);
      } else {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.paos_organisaatio_oid === this.lapsi.paos_organisaatio_oid);
      }
    }
  }

  saveVarhaiskasvatussuhde(form: FormGroup): void {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const varhaiskasvatussuhdeJson: VardaVarhaiskasvatussuhdeDTO = {
        ...form.value,
        toimipaikka: form.value.toimipaikka || this.varhaiskasvatussuhde.toimipaikka,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (this.varhaiskasvatussuhde) {
        this.lapsiService.updateVarhaiskasvatussuhde(varhaiskasvatussuhdeJson).subscribe({
          next: () => {
            this.togglePanel(false, true, true);
            this.snackBarService.success(this.i18n.varhaiskasvatussuhde_save_success);
            this.lapsiService.sendLapsiListUpdate();
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      } else {
        this.lapsiService.createVarhaiskasvatussuhde(varhaiskasvatussuhdeJson).subscribe({
          next: () => {
            this.togglePanel(false, true, true);
            this.snackBarService.success(this.i18n.varhaiskasvatussuhde_save_success);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      }
    } else {
      this.disableSubmit();
    }
  }

  deleteVarhaiskasvatussuhde(): void {
    this.lapsiService.deleteVarhaiskasvatussuhde(this.varhaiskasvatussuhde.id).subscribe({
      next: () => {
        this.togglePanel(false, true, true);
        this.snackBarService.warning(this.i18n.varhaiskasvatussuhde_delete_success);
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
    if (this.varhaiskasvatussuhde) {
      this.formGroup.controls.toimipaikka.disable();
    }
  }

  initToimipaikat() {
    const { toimipaikat, tallentajaToimipaikat } = this.vardaVakajarjestajaService.getFilteredToimipaikat();
    if (this.varhaiskasvatussuhde && !this.toimijaAccess.lapsitiedot.tallentaja) {
      this.toimipaikat = toimipaikat;
    } else {
      this.toimipaikat = tallentajaToimipaikat.filter(toimipaikka => {
        const access = this.authService.getUserAccess(toimipaikka.organisaatio_oid);
        return access.lapsitiedot.tallentaja;
      });
    }
  }

  initDateFilters() {
    if (this.varhaiskasvatuspaatos) {
      this.startDateRange.min = new Date(this.varhaiskasvatuspaatos.alkamis_pvm);
      this.startDateChange(this.formGroup.controls.alkamis_pvm?.value);

      if (this.varhaiskasvatuspaatos.paattymis_pvm) {
        this.startDateRange.max = new Date(this.varhaiskasvatuspaatos.paattymis_pvm);
        this.endDateRange.max = new Date(this.varhaiskasvatuspaatos.paattymis_pvm);
      }
    }
  }

  startDateChange(startDate: Moment) {
    this.endDateRange.min = startDate?.clone().toDate() || new Date(this.varhaiskasvatuspaatos.alkamis_pvm);
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  sendUpdateList() {
    this.lapsiService.sendLapsiListUpdate();
  }
}
