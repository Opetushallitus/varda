import { Component, OnInit, OnChanges, Input, Output, ViewChildren, EventEmitter, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaTaydennyskoulutusDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { Observable } from 'rxjs';
import { ErrorTree, HenkilostoErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import * as moment from 'moment';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { KoodistoDTO } from 'projects/varda-shared/src/lib/dto/koodisto-models';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from '../../../../services/varda-date.service';

@Component({
  selector: 'app-varda-tyontekija-taydennyskoulutus',
  templateUrl: './varda-tyontekija-taydennyskoulutus.component.html',
  styleUrls: [
    './varda-tyontekija-taydennyskoulutus.component.css',
    '../varda-tyontekija-taydennyskoulutukset.component.css',
    '../../varda-tyontekija-form.component.css'
  ]
})
export class VardaTyontekijaTaydennyskoulutusComponent implements OnInit, AfterViewInit {
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
  isEdit: boolean;
  tehtavanimike_koodi: string;
  taydennyskoulutusFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService = new HenkilostoErrorMessageService();

  constructor(
    private el: ElementRef,
    private henkilostoService: VardaHenkilostoApiService
  ) {
    this.element = this.el;
    this.taydennyskoulutusFormErrors = this.henkilostoErrorService.initErrorList();

  }

  ngOnInit() {
    this.expandPanel = !this.taydennyskoulutus;
    this.tehtavanimike_koodi = this.taydennyskoulutus?.taydennyskoulutus_tyontekijat.find(tyontekija => tyontekija.tyontekija === this.tyontekija.url).tehtavanimike_koodi;

    this.taydennyskoulutusForm = new FormGroup({
      id: new FormControl(this.taydennyskoulutus?.id),
      lahdejarjestelma: new FormControl(this.taydennyskoulutus?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      nimi: new FormControl(this.taydennyskoulutus?.nimi, Validators.required),
      koulutuspaivia: new FormControl(this.taydennyskoulutus?.koulutuspaivia, [Validators.required, Validators.min(0.5), Validators.max(160), VardaFormValidators.remainderOf(0.5)]),
      suoritus_pvm: new FormControl(this.taydennyskoulutus ? moment(this.taydennyskoulutus?.suoritus_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      tehtavanimike_koodi: new FormControl(this.tehtavanimike_koodi || null, Validators.required),
    });

    if (!this.toimipaikkaAccess.taydennyskoulutustiedot.tallentaja || this.taydennyskoulutus) {
      this.disableForm();
    } else {
      this.enableForm();
    }
  }

  ngAfterViewInit() {
    if (!this.taydennyskoulutus) {
      this.panelHeader?.focus();
    }
  }


  saveTaydennyskoulutus(form: FormGroup) {
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (HenkilostoErrorMessageService.formIsValid(form)) {
      const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
        ...form.value,
        suoritus_pvm: form.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      if (this.taydennyskoulutus) {
        if (this.tehtavanimike_koodi !== form.value.tehtavanimike_koodi) {
          taydennyskoulutusJson.taydennyskoulutus_tyontekijat_add = [{ tyontekija: this.tyontekija.url, tehtavanimike_koodi: form.value.tehtavanimike_koodi }];
        }

        this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: () => {
            if (this.tehtavanimike_koodi !== form.value.tehtavanimike_koodi) {
              this.deleteTaydennyskoulutus();
            } else {
              this.togglePanel(false, true);
            }
          },
          error: err => this.henkilostoErrorService.handleError(err)
        });
      } else {
        taydennyskoulutusJson.taydennyskoulutus_tyontekijat = [{ tyontekija: this.tyontekija.url, tehtavanimike_koodi: form.value.tehtavanimike_koodi }];

        this.henkilostoService.createTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: () => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      }

    }
  }


  deleteTaydennyskoulutus(): void {
    const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
      ...this.taydennyskoulutusForm.value,
      suoritus_pvm: this.taydennyskoulutusForm.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat),
      taydennyskoulutus_tyontekijat_remove: this.getExistingRecords()
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
  }

  enableForm() {
    this.isEdit = true;
    this.taydennyskoulutusForm.enable();
  }


  getExistingRecords() {
    return this.taydennyskoulutus.taydennyskoulutus_tyontekijat
      .filter(tyontekija => tyontekija.tyontekija === this.tyontekija.url)
      .map(tyontekija => {
        return {
          tyontekija: tyontekija.tyontekija,
          tehtavanimike_koodi: this.tehtavanimike_koodi
        };
      });
  }
}
