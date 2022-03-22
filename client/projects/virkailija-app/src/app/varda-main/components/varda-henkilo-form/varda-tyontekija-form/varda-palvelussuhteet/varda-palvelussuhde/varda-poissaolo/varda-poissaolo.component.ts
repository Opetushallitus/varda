import { Component, OnInit, Input, ViewChild, OnDestroy, Output, EventEmitter } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import * as moment from 'moment';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { finalize, Observable, Subscription } from 'rxjs';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from 'varda-shared';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { Moment } from 'moment';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import {
  TyontekijaPalvelussuhde,
  TyontekijaPidempiPoissaolo
} from '../../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaPidempiPoissaoloDTO } from '../../../../../../../utilities/models/dto/varda-tyontekija-dto.model';

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
export class VardaPoissaoloComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnDestroy {
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() palvelussuhde: TyontekijaPalvelussuhde;
  @Input() pidempiPoissaolo: TyontekijaPidempiPoissaolo;
  @Output() addObject = new EventEmitter<TyontekijaPidempiPoissaolo>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  isSubmitting = false;
  endDateRange = { min: VardaDateService.henkilostoReleaseDate, max: null };
  poissaoloFormErrors: Observable<Array<ErrorTree>>;

  private henkilostoErrorService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.poissaoloFormErrors = this.henkilostoErrorService.initErrorList();
  }

  ngOnInit() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.pidempiPoissaolo?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      palvelussuhde: new FormControl(this.henkilostoService.getPalvelussuhdeUrl(this.palvelussuhde.id)),
      alkamis_pvm: new FormControl(this.pidempiPoissaolo ? moment(this.pidempiPoissaolo?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.pidempiPoissaolo ? moment(this.pidempiPoissaolo?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
    });

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );

    if (this.pidempiPoissaolo) {
      this.disableForm();
    } else {
      this.enableForm();
      this.togglePanel(true);
      this.panelHeader?.focus();
    }

    this.checkFormErrors(this.henkilostoService, 'pidempipoissaolo', this.pidempiPoissaolo?.id);
  }

  savePoissaolo(form: FormGroup) {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const poissaoloJson: VardaPidempiPoissaoloDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      const observable = this.pidempiPoissaolo ? this.henkilostoService.updatePoissaolo(poissaoloJson) :
        this.henkilostoService.createPoissaolo(poissaoloJson);
      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            if (!this.pidempiPoissaolo) {
              // Close panel if object was created
              this.togglePanel(false);
            }
            this.snackBarService.success(this.i18n.poissaolo_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();

            this.pidempiPoissaolo = result;
            this.addObject.emit(this.pidempiPoissaolo);
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
      this.henkilostoService.deletePoissaolo(this.pidempiPoissaolo.id).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.poissaolo_delete_success);
          this.henkilostoService.sendHenkilostoListUpdate();
          this.deleteObject.emit(this.pidempiPoissaolo.id);
        },
        error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
      })
    );
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 500);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
  }

  startDateChange(startDate: Moment) {
    const endDate = startDate?.clone().add(59, 'days');
    this.endDateRange.min = endDate?.toDate() || VardaDateService.henkilostoReleaseDate;
    if (this.endDateRange.min < VardaDateService.henkilostoReleaseDate) {
      this.endDateRange.min = VardaDateService.henkilostoReleaseDate;
    }

    setTimeout(() => this.formGroup.controls.paattymis_pvm?.updateValueAndValidity(), 100);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
}
