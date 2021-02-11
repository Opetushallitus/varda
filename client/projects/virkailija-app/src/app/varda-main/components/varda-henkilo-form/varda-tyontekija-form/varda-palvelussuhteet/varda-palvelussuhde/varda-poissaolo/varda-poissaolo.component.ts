import { Component, OnInit, Input, Output, EventEmitter, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaPoissaoloDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-poissolo-dto.model';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import * as moment from 'moment';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from 'projects/virkailija-app/src/app/varda-main/services/varda-date.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { Moment } from 'moment';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaHenkiloFormAccordionAbstractComponent } from '../../../../varda-henkilo-form-accordion/varda-henkilo-form-accordion.abstract';

@Component({
  selector: 'app-varda-poissaolo',
  templateUrl: './varda-poissaolo.component.html',
  styleUrls: [
    './varda-poissaolo.component.css',
    '../varda-palvelussuhde.component.css',
    '../../../varda-tyontekija-form.component.css',
    '../../../../varda-henkilo-form.component.css'
  ]
})
export class VardaPoissaoloComponent extends VardaHenkiloFormAccordionAbstractComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() palvelussuhde: VardaPalvelussuhdeDTO;
  @Input() poissaolo: VardaPoissaoloDTO;
  @Output() closePoissaolo = new EventEmitter<boolean>(true);
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  expandPanel: boolean;
  poissaoloForm: FormGroup;
  isSubmitting = new BehaviorSubject<boolean>(false);
  subscriptions: Array<Subscription> = [];
  i18n = VirkailijaTranslations;
  isEdit: boolean;
  endDateRange = { min: VardaDateService.henkilostoReleaseDate, max: null };

  poissaoloFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private modalService: VardaModalService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService
  ) {
    super();
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.poissaoloFormErrors = this.henkilostoErrorService.initErrorList();
  }


  ngOnInit() {
    this.expandPanel = !this.poissaolo;

    this.poissaoloForm = new FormGroup({
      id: new FormControl(this.poissaolo?.id),
      lahdejarjestelma: new FormControl(this.poissaolo?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      palvelussuhde: new FormControl(this.palvelussuhde.url),
      alkamis_pvm: new FormControl(this.poissaolo ? moment(this.poissaolo?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.poissaolo ? moment(this.poissaolo?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
    });

    if (!this.toimipaikkaAccess.tyontekijatiedot.tallentaja || this.poissaolo) {
      this.disableForm();
    } else {
      this.enableForm();
    }

    this.checkFormErrors(this.henkilostoService, 'poissaolo', this.poissaolo?.id);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngAfterViewInit() {
    if (!this.poissaolo) {
      this.panelHeader?.focus();
    }

    this.subscriptions.push(
      this.poissaoloForm.statusChanges
        .pipe(filter(() => !this.poissaoloForm.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }


  savePoissaolo(form: FormGroup) {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const poissaoloJson: VardaPoissaoloDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      if (this.poissaolo) {
        this.henkilostoService.updatePoissaolo(poissaoloJson).subscribe({
          next: poissaoloData => {
            this.togglePanel(false, true);
            this.snackBarService.success(this.i18n.poissaolo_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      } else {
        this.henkilostoService.createPoissaolo(poissaoloJson).subscribe({
          next: poissaoloData => {
            this.togglePanel(false, true);
            this.snackBarService.success(this.i18n.poissaolo_save_success);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => this.disableSubmit());
      }

    } else {
      this.disableSubmit();
    }
  }

  deletePoissaolo(): void {
    this.henkilostoService.deletePoissaolo(this.poissaolo.id).subscribe({
      next: deleted => {
        this.togglePanel(false, true);
        this.snackBarService.warning(this.i18n.poissaolo_delete_success);
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  togglePanel(open: boolean, refreshList?: boolean) {
    this.expandPanel = open;

    if (!open || refreshList) {
      this.disableForm();
      this.closePoissaolo?.emit(refreshList);
      if (refreshList) {
        this.henkilostoService.sendHenkilostoListUpdate();
      }
    }
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
  }

  disableForm() {
    this.isEdit = false;
    this.poissaoloForm.disable();
    this.modalService.setFormValuesChanged(false);
  }

  enableForm() {
    this.isEdit = true;
    this.poissaoloForm.enable();
  }

  startDateChange(startDate: Moment) {
    const endDate = startDate?.clone().add(59, 'days');
    this.endDateRange.min = endDate?.toDate() || VardaDateService.henkilostoReleaseDate;
    if (this.endDateRange.min < VardaDateService.henkilostoReleaseDate) {
      this.endDateRange.min = VardaDateService.henkilostoReleaseDate;
    }

    setTimeout(() => this.poissaoloForm.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }
}
