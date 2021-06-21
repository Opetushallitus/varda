import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';
import { FormGroup, Validators } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { VardaToimipaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, Observable } from 'rxjs';
import { KoodistoEnum } from 'varda-shared';
import { MatExpansionPanel } from '@angular/material/expansion';
import { VardaFormAccordionAbstractComponent } from '../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import { VardaModalService } from '../../../../core/services/varda-modal.service';

@Component({
  template: '',
})
export abstract class PainotusAbstractComponent<T> extends VardaFormAccordionAbstractComponent implements OnChanges {
  @ViewChild('matPanel') matPanel: MatExpansionPanel;
  @Input() toimipaikka: VardaToimipaikkaDTO;
  @Input() painotus: T;
  @Input() saveAccess: boolean;
  @Input() minStartDate: Date;
  @Input() maxEndDate: Date;
  @Output() refreshList = new EventEmitter<boolean>(true);
  @Output() pendingPainotus = new EventEmitter<T>(true);
  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;
  formGroup: FormGroup;
  isEdit: boolean;
  isSubmitting = new BehaviorSubject<boolean>(false);
  startDateRange = { min: null, max: null };
  endDateRange = { min: null, max: null };
  savePending: boolean;
  formErrors: Observable<Array<ErrorTree>>;
  protected errorService: VardaErrorMessageService;

  constructor(
    protected translateService: TranslateService,
    protected vakajarjestajaApiService: VardaVakajarjestajaApiService,
    protected snackBarService: VardaSnackBarService,
    modalService: VardaModalService,
  ) {
    super(modalService);
    this.errorService = new VardaErrorMessageService(translateService);
    this.formErrors = this.errorService.initErrorList();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.formGroup) {
      this.init();
    } else if (changes.toimipaikka?.currentValue) {
      this.initDateFilters();

      if (changes.toimipaikka.currentValue.id && !changes.toimipaikka?.previousValue?.id) {
        if (this.savePending) {
          this.painotus = null;
          this.enableForm();
          this.savePainotus(this.formGroup, true);
        }
      }
    }

    if (changes.saveAccess) {
      if (!changes.saveAccess.currentValue) {
        this.disableForm();
      }
    }
  }

  init() {
    if (!this.painotus) {
      this.togglePanel(true, undefined, true);
    }

    this.initForm();

    if (!this.saveAccess || this.painotus) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.initDateFilters();
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
  }

  enableForm() {
    this.isEdit = true;
    this.savePending = false;
    this.formGroup.enable();
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

  sendUpdateList() {
    this.vakajarjestajaApiService.sendToimipaikkaListUpdate();
  }

  abstract initForm(): void;
  abstract savePainotus(form: FormGroup, wasPending?: boolean): void;
  abstract deletePainotus(): void;
}
