import { Component, OnInit, Input, ViewChild, OnDestroy, Output, EventEmitter } from '@angular/core';
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
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { UserAccess, SaveAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { Subscription, Observable, finalize } from 'rxjs';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { KoodistoDTO, VardaKoodistoService, KoodistoEnum, VardaDateService } from 'varda-shared';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import {
  LapsiKoosteVakapaatos,
  LapsiKoosteVakasuhde
} from '../../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaVarhaiskasvatussuhdeDTO } from '../../../../../../../utilities/models/dto/varda-lapsi-dto.model';

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
export class VardaVarhaiskasvatussuhdeComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnDestroy {
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  @Input() lapsitiedotTallentaja: boolean;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() varhaiskasvatuspaatos: LapsiKoosteVakapaatos;
  @Input() varhaiskasvatussuhde: LapsiKoosteVakasuhde;
  @Output() addObject = new EventEmitter<LapsiKoosteVakasuhde>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  toimijaAccess: UserAccess;
  tehtavanimikkeet: KoodistoDTO;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  isSubmitting = false;
  startDateRange = { min: null, max: null };
  endDateRange = { min: null, max: null };
  varhaiskasvatussuhdeFormErrors: Observable<Array<ErrorTree>>;

  private errorMessageService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

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
    this.errorMessageService = new VardaErrorMessageService(translateService);
    this.varhaiskasvatussuhdeFormErrors = this.errorMessageService.initErrorList();
    this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike).subscribe(koodisto => this.tehtavanimikkeet = koodisto);
    this.initToimipaikat();
  }

  ngOnInit() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.varhaiskasvatussuhde?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      varhaiskasvatuspaatos: new FormControl(this.lapsiService.getVarhaiskasvatuspaatosUrl(this.varhaiskasvatuspaatos.id), Validators.required),
      alkamis_pvm: new FormControl(this.varhaiskasvatussuhde ? moment(this.varhaiskasvatussuhde?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(
        this.varhaiskasvatussuhde?.paattymis_pvm ? moment(this.varhaiskasvatussuhde?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null,
        this.varhaiskasvatuspaatos.paattymis_pvm ? [Validators.required] : null),
      toimipaikka_oid: new FormControl(this.varhaiskasvatussuhde?.toimipaikka_oid || this.henkilonToimipaikka?.organisaatio_oid, Validators.required),
    });

    if (this.varhaiskasvatussuhde) {
      this.disableForm();
    } else {
      this.togglePanel(true);
      this.enableForm();
      this.panelHeader?.focus();
    }

    this.checkFormErrors(this.lapsiService, 'varhaiskasvatussuhde', this.varhaiskasvatussuhde?.id);

    this.initDateFilters();

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

    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    if (activeLapsi?.tallentaja_organisaatio_oid) {
      const vakajarjestajaOID = this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid;
      if (activeLapsi.paos_organisaatio_oid === vakajarjestajaOID) {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => !toimipaikka.paos_organisaatio_url);
      } else {
        this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.paos_organisaatio_oid === activeLapsi.paos_organisaatio_oid);
      }
    }

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  saveVarhaiskasvatussuhde(form: FormGroup): void {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.errorMessageService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const varhaiskasvatussuhdeJson: VardaVarhaiskasvatussuhdeDTO = {
        ...form.value,
        toimipaikka_oid: form.value.toimipaikka_oid || this.varhaiskasvatussuhde.toimipaikka_oid,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      const observable = this.varhaiskasvatussuhde ? this.lapsiService.updateVarhaiskasvatussuhde(varhaiskasvatussuhdeJson) :
        this.lapsiService.createVarhaiskasvatussuhde(varhaiskasvatussuhdeJson);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.varhaiskasvatussuhde) {
              // Close panel if object was created
              this.togglePanel(false);
            }

            this.snackBarService.success(this.i18n.varhaiskasvatussuhde_save_success);
            this.lapsiService.sendLapsiListUpdate();
            this.varhaiskasvatussuhde = {...result, toimipaikka_nimi: ''};
            this.addObject.emit(this.varhaiskasvatussuhde);
          },
          error: err => this.errorMessageService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deleteVarhaiskasvatussuhde(): void {
    this.subscriptions.push(
      this.lapsiService.deleteVarhaiskasvatussuhde(this.varhaiskasvatussuhde.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.varhaiskasvatussuhde_delete_success);
          this.lapsiService.sendLapsiListUpdate();
          this.deleteObject.emit(this.varhaiskasvatussuhde.id);
        },
        error: err => this.errorMessageService.handleError(err, this.snackBarService)
      })
    );
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 500);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
    if (this.varhaiskasvatussuhde) {
      this.formGroup.controls.toimipaikka_oid.disable();
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

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
}
