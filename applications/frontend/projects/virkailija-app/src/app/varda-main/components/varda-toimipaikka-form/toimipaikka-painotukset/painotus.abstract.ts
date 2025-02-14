import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormGroup, Validators } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { ToimipaikkaKooste } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { Observable } from 'rxjs';
import { KoodistoEnum } from 'varda-shared';
import { VardaFormAccordionAbstractComponent } from '../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import { VardaModalService } from '../../../../core/services/varda-modal.service';
import { VardaUtilityService } from '../../../../core/services/varda-utility.service';

@Component({
  template: '',
})
export abstract class PainotusAbstractComponent<T> extends VardaFormAccordionAbstractComponent<T> implements OnInit, OnChanges {
  @Input() toimipaikka: ToimipaikkaKooste;
  @Input() saveAccess: boolean;
  @Input() minStartDate: Date;
  @Input() maxEndDate: Date;
  @Output() addObject = new EventEmitter<T>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  koodistoEnum = KoodistoEnum;
  startDateRange = {min: null, max: null};
  endDateRange = {min: null, max: null};
  savePending: boolean;
  formErrors: Observable<Array<ErrorTree>>;

  protected errorService: VardaErrorMessageService;

  constructor(
    protected translateService: TranslateService,
    protected vakajarjestajaApiService: VardaVakajarjestajaApiService,
    protected snackBarService: VardaSnackBarService,
    modalService: VardaModalService,
    utilityService: VardaUtilityService
  ) {
    super(modalService, utilityService);
    this.apiService = this.vakajarjestajaApiService;
    this.errorService = new VardaErrorMessageService(translateService);
    this.formErrors = this.errorService.initErrorList();
  }

  ngOnInit() {
    super.ngOnInit();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Run after form has been initialized
    if (this.formGroup) {
      if (changes.minStartDate || changes.maxEndDate) {
        this.initDateFilters();
      }

      if (changes.toimipaikka?.currentValue?.id && !changes.toimipaikka?.previousValue?.id) {
        // Toimipaikka was created so start saving painotus objects
        if (this.savePending) {
          this.currentObject = null;
          this.enableForm();
          this.savePainotus(this.formGroup, true);
        }
      }
    }
  }

  enableFormExtra() {
    this.savePending = false;
  }

  initDateFilters() {
    this.startDateRange.min = new Date(this.minStartDate);
    this.endDateRange.max = this.maxEndDate;
    this.startDateChange(moment(this.minStartDate?.valueOf()));

    this.startDateRange.max = new Date(this.maxEndDate);

    const paattymisPvmControl = this.formGroup.controls.paattymis_pvm;
    paattymisPvmControl.setValidators(this.toimipaikka?.paattymis_pvm ? Validators.required : null);
    paattymisPvmControl.updateValueAndValidity();
  }

  startDateChange(startDate: moment.Moment) {
    const endDate = startDate?.clone().add(1, 'days');
    this.endDateRange.min = endDate?.toDate() || this.maxEndDate;
    if (this.endDateRange?.max < this.endDateRange?.min) {
      this.endDateRange.min = this.endDateRange.max;
    }
    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  abstract savePainotus(form: FormGroup, wasPending?: boolean): void;
  abstract deletePainotus(): void;
}
