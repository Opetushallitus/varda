import { Component, OnInit, OnChanges, Input, Output, ViewChildren, EventEmitter, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaTaydennyskoulutusDTO, VardaTaydennyskoulutusTyontekijaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { Observable, Subscription } from 'rxjs';
import { ErrorTree, HenkilostoErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import * as moment from 'moment';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { KoodistoDTO } from 'projects/varda-shared/src/lib/dto/koodisto-models';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from '../../../../services/varda-date.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { filter, distinctUntilChanged } from 'rxjs/operators';

@Component({
  selector: 'app-varda-tyontekija-taydennyskoulutus',
  templateUrl: './varda-tyontekija-taydennyskoulutus.component.html',
  styleUrls: [
    './varda-tyontekija-taydennyskoulutus.component.css',
    '../varda-tyontekija-taydennyskoulutukset.component.css',
    '../../varda-tyontekija-form.component.css'
  ]
})
export class VardaTyontekijaTaydennyskoulutusComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() taydennyskoulutus: VardaTaydennyskoulutusDTO;
  @Input() tehtavanimikkeet: KoodistoDTO;
  @Input() henkilonTutkinnot: Array<VardaTutkintoDTO>;
  @Output() closeTaydennyskoulutus = new EventEmitter<boolean>(true);
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  i18n = VirkailijaTranslations;
  element: ElementRef;
  expandPanel: boolean;
  taydennyskoulutusForm: FormGroup;
  subscriptions: Array<Subscription> = [];
  isEdit: boolean;
  tehtavanimike_koodit: Array<string>;
  taydennyskoulutusFormErrors: Observable<Array<ErrorTree>>;
  limitedEditAccess: boolean;
  firstAllowedDate = VardaDateService.henkilostoReleaseDate;
  private henkilostoErrorService = new HenkilostoErrorMessageService();

  constructor(
    private el: ElementRef,
    private henkilostoService: VardaHenkilostoApiService,
    private modalService: VardaModalService
  ) {
    this.element = this.el;
    this.taydennyskoulutusFormErrors = this.henkilostoErrorService.initErrorList();

  }

  ngOnInit() {
    this.expandPanel = !this.taydennyskoulutus;
    this.tehtavanimike_koodit = this.taydennyskoulutus?.taydennyskoulutus_tyontekijat.
      filter(tyontekija => tyontekija.henkilo_oid === this.tyontekija.henkilo_oid)
      .map(tyontekija => tyontekija.tehtavanimike_koodi) || [];

    this.taydennyskoulutusForm = new FormGroup({
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
      this.taydennyskoulutusForm.statusChanges
        .pipe(filter(() => !this.taydennyskoulutusForm.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }


  saveTaydennyskoulutus(form: FormGroup) {
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (HenkilostoErrorMessageService.formIsValid(form)) {
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
          next: () => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      } else {
        taydennyskoulutusJson.taydennyskoulutus_tyontekijat = tehtavanimikkeetToAdd;

        this.henkilostoService.createTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: () => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      }

    }
  }


  deleteTaydennyskoulutus(nimikkeetToDelete?: Array<VardaTaydennyskoulutusTyontekijaDTO>): void {
    const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
      ...this.taydennyskoulutusForm.value,
      suoritus_pvm: this.taydennyskoulutusForm.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat),
      taydennyskoulutus_tyontekijat_remove: nimikkeetToDelete || this.compareTehtavanimikkeet(this.tehtavanimike_koodit)
    };

    this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson).subscribe({
      next: () => this.togglePanel(false, true),
      error: err => {
        try {
          if (err.error?.taydennyskoulutus_tyontekijat_remove?.includes('Cannot delete all tyontekijat from taydennyskoulutus')) {
            this.henkilostoService.deleteTaydennyskoulutus(parseInt(this.taydennyskoulutus.id)).subscribe({
              next: deleted => this.togglePanel(false, true),
              error: subErr => this.henkilostoErrorService.handleError(subErr)
            });
          } else {
            this.henkilostoErrorService.handleError(err);
          }
        } catch (catchErr) {
          this.henkilostoErrorService.handleError(err);
        }
      }
    });
  }

  togglePanel(open: boolean, refreshList?: boolean) {
    this.expandPanel = open;

    if (!open || refreshList) {
      this.disableForm();
      this.closeTaydennyskoulutus?.emit(refreshList);
    }
  }

  disableForm() {
    this.isEdit = false;
    this.taydennyskoulutusForm.disable();
    this.modalService.setFormValuesChanged(false);
  }

  enableForm() {
    this.isEdit = true;
    this.taydennyskoulutusForm.enable();
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
