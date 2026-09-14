import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { DateTime } from 'luxon';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { finalize, Observable } from 'rxjs';
import {
  ErrorTree,
  VardaErrorMessageService
} from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from 'varda-shared';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import {
  TyontekijaPalvelussuhde,
  TyontekijaPidempiPoissaolo
} from '../../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaPidempiPoissaoloDTO } from '../../../../../../../utilities/models/dto/varda-tyontekija-dto.model';
import { VardaUtilityService } from '../../../../../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../../../../../utilities/models/enums/model-name.enum';

@Component({
    selector: 'app-varda-poissaolo',
    templateUrl: './varda-poissaolo.component.html',
    styleUrls: [
        './varda-poissaolo.component.css',
        '../varda-palvelussuhde.component.css',
        '../../../varda-tyontekija-form.component.css',
        '../../../../varda-henkilo-form.component.css'
    ],
    standalone: false
})
export class VardaPoissaoloComponent extends VardaFormAccordionAbstractComponent<TyontekijaPidempiPoissaolo> implements OnInit {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() palvelussuhde: TyontekijaPalvelussuhde;
  @Output() addObject = new EventEmitter<TyontekijaPidempiPoissaolo>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  endDateRange = { min: VardaDateService.henkilostoReleaseDate, max: null };
  poissaoloFormErrors: Observable<Array<ErrorTree>>;
  modelName = ModelNameEnum.PIDEMPI_POISSAOLO;

  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
    utilityService: VardaUtilityService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService, utilityService);
    this.apiService = this.henkilostoService;
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.poissaoloFormErrors = this.henkilostoErrorService.initErrorList();
  }

  ngOnInit() {
    super.ngOnInit();
  }

  initForm() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.currentObject?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      palvelussuhde: new FormControl(this.henkilostoService.getPalvelussuhdeUrl(this.palvelussuhde.id)),
      alkamis_pvm: new FormControl(
        this.currentObject
          ? DateTime.fromFormat(this.currentObject.alkamis_pvm, VardaDateService.vardaApiDateFormat, VardaDateService.uiDateTimezone)
          : null,
        Validators.required
      ),
      paattymis_pvm: new FormControl(
        this.currentObject
          ? DateTime.fromFormat(this.currentObject.paattymis_pvm, VardaDateService.vardaApiDateFormat, VardaDateService.uiDateTimezone)
          : null,
        Validators.required
      ),
    });
  }

  savePoissaolo(form: FormGroup) {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const poissaoloJson: VardaPidempiPoissaoloDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.toFormat(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm.toFormat(VardaDateService.vardaApiDateFormat)
      };

      const observable = this.currentObject ? this.henkilostoService.updatePoissaolo(poissaoloJson) :
        this.henkilostoService.createPoissaolo(poissaoloJson);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.currentObject) {
              // Close panel if object was created
              this.togglePanel(false);
            }
            this.snackBarService.success(this.i18n.poissaolo_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();

            this.currentObject = result;
            this.addObject.emit(this.currentObject);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deletePoissaolo(): void {
    this.subscriptions.push(
      this.henkilostoService.deletePoissaolo(this.currentObject.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.poissaolo_delete_success);
          this.henkilostoService.sendHenkilostoListUpdate();
          this.deleteObject.emit(this.currentObject.id);
        },
        error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
      })
    );
  }

  startDateChange(startDate: DateTime) {
    const endDate = startDate?.plus({ days: 59 });
    this.endDateRange.min = endDate?.toJSDate() || VardaDateService.henkilostoReleaseDate;
    if (this.endDateRange.min < VardaDateService.henkilostoReleaseDate) {
      this.endDateRange.min = VardaDateService.henkilostoReleaseDate;
    }

    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }
}
