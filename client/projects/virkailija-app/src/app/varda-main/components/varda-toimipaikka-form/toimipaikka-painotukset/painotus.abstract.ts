import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { ErrorTree, HenkilostoErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { KielipainotusDTO, ToiminnallinenPainotusDTO, VardaToimipaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, Observable } from 'rxjs';
import { KoodistoEnum } from 'varda-shared';

@Component({
  template: '',
})
export abstract class PainotusAbstractComponent<T> implements OnChanges {
  @Input() toimipaikka: VardaToimipaikkaDTO;
  @Input() painotus: T;
  @Input() saveAccess: boolean;
  @Input() minStartDate: Date;
  @Input() maxEndDate: Date;
  @Output() refreshList = new EventEmitter<boolean>(true);
  @Output() pendingPainotus = new EventEmitter<T>(true);
  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;
  expandPanel: boolean;
  painotusForm: FormGroup;
  isEdit: boolean;
  isSubmitting = new BehaviorSubject<boolean>(false);
  startDateRange = { min: null, max: null };
  endDateRange = { min: null, max: null };
  savePending: boolean;
  formErrors: Observable<Array<ErrorTree>>;
  protected errorService: HenkilostoErrorMessageService;

  constructor(
    protected translateService: TranslateService,
    protected vakajarjestajaApiService: VardaVakajarjestajaApiService,
    protected snackBarService: VardaSnackBarService
  ) {
    this.errorService = new HenkilostoErrorMessageService(translateService);
    this.formErrors = this.errorService.initErrorList();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.painotusForm) {
      this.init();
    } else if (changes.toimipaikka?.currentValue) {
      this.initDateFilters();

      if (changes.toimipaikka.currentValue.id && !changes.toimipaikka?.previousValue?.id) {
        if (this.savePending) {
          this.painotus = null;
          this.enableForm();
          this.savePainotus(this.painotusForm, true);
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
    this.expandPanel = !this.painotus;

    this.initForm();

    if (!this.saveAccess || this.painotus) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.initDateFilters();
  }

  togglePanel(open: boolean, refreshList?: boolean) {
    this.expandPanel = open;

    if (!open || refreshList) {
      this.disableForm();
      this.refreshList?.emit(refreshList);
    }
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
  }

  disableForm() {
    this.isEdit = false;
    this.painotusForm.disable();
  }

  enableForm() {
    this.isEdit = true;
    this.savePending = false;
    this.painotusForm.enable();
  }


  initDateFilters() {
    this.startDateRange.min = new Date(this.minStartDate);
    this.endDateRange.max = this.maxEndDate;
    this.startDateChange(moment(this.minStartDate?.valueOf()));

    this.startDateRange.max = new Date(this.maxEndDate);
  }

  startDateChange(startDate: moment.Moment) {
    const endDate = startDate?.clone().add(1, 'days');
    this.endDateRange.min = endDate?.toDate() || this.maxEndDate;
    if (this.endDateRange?.max < this.endDateRange?.min) {
      this.endDateRange.min = this.endDateRange.max;
    }
    setTimeout(() => this.painotusForm.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  abstract initForm(): void;
  abstract savePainotus(form: FormGroup, wasPending?: boolean): void;
  abstract deletePainotus(): void;
}
