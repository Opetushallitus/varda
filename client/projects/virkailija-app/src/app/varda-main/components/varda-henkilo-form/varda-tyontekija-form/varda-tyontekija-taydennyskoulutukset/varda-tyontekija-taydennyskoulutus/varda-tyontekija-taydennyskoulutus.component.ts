import { Component, OnInit, Input, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaTaydennyskoulutusDTO, VardaTaydennyskoulutusTyontekijaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import * as moment from 'moment';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { KoodistoDTO } from 'projects/varda-shared/src/lib/models/koodisto-models';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { filter, distinctUntilChanged } from 'rxjs/operators';
import { VardaDateService } from 'projects/virkailija-app/src/app/varda-main/services/varda-date.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';

@Component({
  selector: 'app-varda-tyontekija-taydennyskoulutus',
  templateUrl: './varda-tyontekija-taydennyskoulutus.component.html',
  styleUrls: [
    './varda-tyontekija-taydennyskoulutus.component.css',
    '../varda-tyontekija-taydennyskoulutukset.component.css',
    '../../varda-tyontekija-form.component.css',
    '../../../varda-henkilo-form.component.css'
  ]
})
export class VardaTyontekijaTaydennyskoulutusComponent extends VardaFormAccordionAbstractComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() taydennyskoulutus: VardaTaydennyskoulutusDTO;
  @Input() tehtavanimikkeet: KoodistoDTO;
  @Input() henkilonTutkinnot: Array<VardaTutkintoDTO>;
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  element: ElementRef;
  subscriptions: Array<Subscription> = [];
  tehtavanimike_koodit: Array<string>;
  isSubmitting = new BehaviorSubject<boolean>(false);
  taydennyskoulutusFormErrors: Observable<Array<ErrorTree>>;
  limitedEditAccess: boolean;
  firstAllowedDate = VardaDateService.henkilostoReleaseDate;
  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private el: ElementRef,
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.element = this.el;
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.taydennyskoulutusFormErrors = this.henkilostoErrorService.initErrorList();

  }

  ngOnInit() {
    if (!this.taydennyskoulutus) {
      this.togglePanel(true, undefined, true);
    }

    this.tehtavanimike_koodit = this.taydennyskoulutus?.taydennyskoulutus_tyontekijat.
      filter(tyontekija => tyontekija.henkilo_oid === this.tyontekija.henkilo_oid)
      .map(tyontekija => tyontekija.tehtavanimike_koodi) || [];

    this.formGroup = new FormGroup({
      id: new FormControl(this.taydennyskoulutus?.id),
      lahdejarjestelma: new FormControl(this.taydennyskoulutus?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      nimi: new FormControl(this.taydennyskoulutus?.nimi, Validators.required),
      koulutuspaivia: new FormControl(this.taydennyskoulutus?.koulutuspaivia, [Validators.required, Validators.min(0.5), Validators.max(160), VardaFormValidators.remainderOf(0.5)]),
      suoritus_pvm: new FormControl(this.taydennyskoulutus ? moment(this.taydennyskoulutus?.suoritus_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      tehtavanimike_koodit: new FormControl(this.tehtavanimike_koodit, Validators.required),
    });

    const tyontekijaNimikeCount = this.taydennyskoulutus?.taydennyskoulutus_tyontekijat.filter(nimike => nimike.henkilo_oid === this.tyontekija.henkilo_oid).length;
    this.limitedEditAccess = this.taydennyskoulutus?.taydennyskoulutus_tyontekijat_count !== tyontekijaNimikeCount;

    if (!this.toimipaikkaAccess.taydennyskoulutustiedot.tallentaja || this.taydennyskoulutus) {
      this.disableForm();
    } else {
      this.enableForm();
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngAfterViewInit() {
    if (!this.taydennyskoulutus) {
      this.panelHeader?.focus();
    }

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  saveTaydennyskoulutus(form: FormGroup) {
    this.isSubmitting.next(true);
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
        ...form.value,
        suoritus_pvm: form.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      const tehtavanimikkeetToAdd = this.compareTehtavanimikkeet(form.value.tehtavanimike_koodit, this.tehtavanimike_koodit);
      const tehtavanimikkeetToRemove = this.compareTehtavanimikkeet(this.tehtavanimike_koodit, form.value.tehtavanimike_koodit);

      if (this.taydennyskoulutus) {
        if (tehtavanimikkeetToAdd.length) {
          taydennyskoulutusJson.taydennyskoulutus_tyontekijat_add = tehtavanimikkeetToAdd;
        }

        if (tehtavanimikkeetToRemove.length) {
          taydennyskoulutusJson.taydennyskoulutus_tyontekijat_remove = tehtavanimikkeetToRemove;
        }

        this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: () => this.togglePanel(false, true, true),
          error: err => this.henkilostoErrorService.handleError(err)
        }).add(() => this.disableSubmit());
      } else {
        taydennyskoulutusJson.taydennyskoulutus_tyontekijat = tehtavanimikkeetToAdd;

        this.henkilostoService.createTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: () => this.togglePanel(false, true, true),
          error: err => this.henkilostoErrorService.handleError(err)
        }).add(() => this.disableSubmit());
      }

    } else {
      this.disableSubmit();
    }
  }

  deleteTaydennyskoulutus(nimikkeetToDelete?: Array<VardaTaydennyskoulutusTyontekijaDTO>): void {
    const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
      ...this.formGroup.value,
      suoritus_pvm: this.formGroup.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat),
      taydennyskoulutus_tyontekijat_remove: nimikkeetToDelete || this.compareTehtavanimikkeet(this.tehtavanimike_koodit)
    };

    this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson).subscribe({
      next: () => {
        this.togglePanel(false, true, true);
        this.snackBarService.warning(this.i18n.taydennyskoulutus_delete_success);
      },
      error: err => {
        try {
          const lastPersonError = err.error.taydennyskoulutus_tyontekijat_remove.find(error => error.error_code === 'TK013');
          if (lastPersonError) {
            this.henkilostoService.deleteTaydennyskoulutus(this.taydennyskoulutus.id).subscribe({
              next: deleted => {
                this.togglePanel(false, true, true);
                this.snackBarService.warning(this.i18n.taydennyskoulutus_delete_success);
              },
              error: subErr => this.henkilostoErrorService.handleError(subErr, this.snackBarService)
            });
          } else {
            this.henkilostoErrorService.handleError(err, this.snackBarService);
          }
        } catch (catchErr) {
          this.henkilostoErrorService.handleError(err, this.snackBarService);
        }
      }
    });
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting.next(false), 500);
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
  }

  compareTehtavanimikkeet(newNimikkeet: Array<string>, existingNimikkeet: Array<string> = []): Array<VardaTaydennyskoulutusTyontekijaDTO> {
    const comparableNimikkeet = newNimikkeet.filter(nimikekoodi => !existingNimikkeet.includes(nimikekoodi)).map(nimikekoodi => {
      return {
        tyontekija: this.tyontekija.url,
        tehtavanimike_koodi: nimikekoodi
      };
    });

    return comparableNimikkeet;
  }
}
