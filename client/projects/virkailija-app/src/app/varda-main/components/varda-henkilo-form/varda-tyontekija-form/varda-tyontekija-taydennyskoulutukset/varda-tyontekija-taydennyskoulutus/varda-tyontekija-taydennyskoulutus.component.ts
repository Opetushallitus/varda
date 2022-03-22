import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaTaydennyskoulutusDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { finalize, Observable, Subscription, throwError } from 'rxjs';
import {
  ErrorTree,
  VardaErrorMessageService
} from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { catchError, distinctUntilChanged, filter } from 'rxjs/operators';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaFormAccordionAbstractComponent } from '../../../../varda-form-accordion-abstract/varda-form-accordion-abstract.component';
import { CodeDTO, KoodistoEnum, VardaDateService } from 'varda-shared';
import { TyontekijaTaydennyskoulutus } from '../../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaVakajarjestajaUi } from '../../../../../../utilities/models/varda-vakajarjestaja-ui.model';
import { VardaVakajarjestajaService } from '../../../../../../core/services/varda-vakajarjestaja.service';
import * as moment from 'moment';

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
export class VardaTyontekijaTaydennyskoulutusComponent extends VardaFormAccordionAbstractComponent implements OnInit, OnChanges, OnDestroy {
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() taydennyskoulutus: TyontekijaTaydennyskoulutus;
  @Input() tehtavanimikeOptions: Array<CodeDTO>;
  @Output() addObject = new EventEmitter<TyontekijaTaydennyskoulutus>(true);
  @Output() deleteObject = new EventEmitter<number>(true);

  element: ElementRef;
  koodistoEnum = KoodistoEnum;
  disabledTehtavanimikeCodes: Array<string> = [];
  isSubmitting = false;
  taydennyskoulutusFormErrors: Observable<Array<ErrorTree>>;
  limitedEditAccess: boolean;
  firstAllowedDate = VardaDateService.henkilostoReleaseDate;
  tyontekijaId: number;
  henkiloOid: string;
  selectedVakajarjestaja: VardaVakajarjestajaUi;

  private henkilostoErrorService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private el: ElementRef,
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    translateService: TranslateService,
    modalService: VardaModalService
  ) {
    super(modalService);
    this.element = this.el;
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.taydennyskoulutusFormErrors = this.henkilostoErrorService.initErrorList();
  }

  ngOnInit() {
    this.formGroup = new FormGroup({
      id: new FormControl(this.taydennyskoulutus?.id),
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      nimi: new FormControl(this.taydennyskoulutus?.nimi, Validators.required),
      koulutuspaivia: new FormControl(this.taydennyskoulutus?.koulutuspaivia, [Validators.required, Validators.min(0.5), Validators.max(160), VardaFormValidators.remainderOf(0.5)]),
      suoritus_pvm: new FormControl(this.taydennyskoulutus ? moment(this.taydennyskoulutus?.suoritus_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      tehtavanimike_koodit: new FormControl(this.taydennyskoulutus?.tehtavanimikeList || [], Validators.required),
    });

    const activeTyontekija = this.henkilostoService.activeTyontekija.getValue();
    this.tyontekijaId = activeTyontekija.id;
    this.henkiloOid = activeTyontekija.henkilo.henkilo_oid;
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.limitedEditAccess = this.taydennyskoulutus?.contains_other_tyontekija;
    this.setDisabledTehtavanimikeCodes();

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );

    if (this.taydennyskoulutus) {
      this.disableForm();
    } else {
      this.enableForm();
      this.togglePanel(true);
      this.panelHeader?.focus();
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.tehtavanimikeOptions) {
      // We do not want this to be called before ngOnInit is called
      setTimeout(() => {
        // Reset tehtavanimike_koodit values just in case
        this.formGroup.controls.tehtavanimike_koodit.setValue(this.taydennyskoulutus?.tehtavanimikeList || []);
        this.setDisabledTehtavanimikeCodes();
      });
    }
  }

  setDisabledTehtavanimikeCodes() {
    this.disabledTehtavanimikeCodes = this.formGroup.controls.tehtavanimike_koodit.value.filter(value =>
      !this.tehtavanimikeOptions.some(code => code.code_value.toLowerCase() === value.toLowerCase()));
  }

  saveTaydennyskoulutus(form: FormGroup) {
    this.isSubmitting = true;
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const taydennyskoulutusJson = {
        ...form.value,
        suoritus_pvm: form.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      let observable;
      if (this.taydennyskoulutus) {
        const tehtavanimikkeetToAdd = this.compareCodeLists(form.value.tehtavanimike_koodit, this.taydennyskoulutus.tehtavanimikeList);
        const tehtavanimikkeetToRemove = this.compareCodeLists(this.taydennyskoulutus.tehtavanimikeList, form.value.tehtavanimike_koodit);
        if (tehtavanimikkeetToAdd.length) {
          taydennyskoulutusJson.taydennyskoulutus_tyontekijat_add = tehtavanimikkeetToAdd;
        }
        if (tehtavanimikkeetToRemove.length) {
          taydennyskoulutusJson.taydennyskoulutus_tyontekijat_remove = tehtavanimikkeetToRemove;
        }
        observable = this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson);
      } else {
        taydennyskoulutusJson.taydennyskoulutus_tyontekijat = this.compareCodeLists(form.value.tehtavanimike_koodit, []);
        observable = this.henkilostoService.createTaydennyskoulutus(taydennyskoulutusJson);
      }

      this.subscriptions.push(
        observable.pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: (result: VardaTaydennyskoulutusDTO) => {
            if (!this.taydennyskoulutus) {
              // Close panel if object was created
              this.togglePanel(false);
            }
            this.snackBarService.success(this.i18n.taydennyskoulutus_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();

            // Rebuild Taydennyskoulutus object as kooste result
            this.taydennyskoulutus = {
              id: result.id,
              tehtavanimikeList: result.taydennyskoulutus_tyontekijat.reduce((filtered, obj) => {
                if (obj.vakajarjestaja_oid === this.selectedVakajarjestaja.organisaatio_oid &&
                  obj.henkilo_oid === this.henkiloOid) {
                  filtered.push(obj.tehtavanimike_koodi);
                }
                return filtered;
              }, []),
              nimi: result.nimi,
              suoritus_pvm: result.suoritus_pvm,
              koulutuspaivia: result.koulutuspaivia,
              contains_other_tyontekija: !!this.taydennyskoulutus?.contains_other_tyontekija
            };

            // Result may contain tehtavanimike codes that were not present previously,
            // kooste API returns only codes that user has permissions to
            this.formGroup.controls.tehtavanimike_koodit.setValue(this.taydennyskoulutus.tehtavanimikeList);
            this.setDisabledTehtavanimikeCodes();
            this.addObject.emit(this.taydennyskoulutus);
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  deleteTaydennyskoulutus(): void {
    const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
      ...this.formGroup.value,
      suoritus_pvm: this.formGroup.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat),
      taydennyskoulutus_tyontekijat_remove: this.compareCodeLists(this.taydennyskoulutus.tehtavanimikeList, [])
    };

    this.subscriptions.push(
      this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson).pipe(
        catchError(err => {
          if (err?.error?.taydennyskoulutus_tyontekijat_remove instanceof Array &&
            err.error.taydennyskoulutus_tyontekijat_remove.find(error => error.error_code === 'TK013')) {
            // Error because Taydennyskoulutus would be left empty, so delete the whole Taydennyskoulutus
            return this.henkilostoService.deleteTaydennyskoulutus(this.taydennyskoulutus.id);
          } else {
            // Rethrow any other error
            return throwError(() => err);
          }
        })
      ).subscribe({
        next: () => {
          this.togglePanel(false);
          this.snackBarService.warning(this.i18n.taydennyskoulutus_delete_success);
          this.henkilostoService.sendHenkilostoListUpdate();
          this.deleteObject.emit(this.taydennyskoulutus.id);
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

  compareCodeLists(newCodes: Array<string>, existingCodes: Array<string> = []): Record<string, any> {
    return newCodes.filter(tehtavanimike => !existingCodes.includes(tehtavanimike)).map(tehtavanimike => ({
      tyontekija: this.henkilostoService.getTyontekijaUrl(this.tyontekijaId),
      tehtavanimike_koodi: tehtavanimike
    }));
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
}
