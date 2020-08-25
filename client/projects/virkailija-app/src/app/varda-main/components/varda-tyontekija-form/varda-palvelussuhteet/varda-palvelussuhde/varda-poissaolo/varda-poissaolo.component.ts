import { Component, OnInit, OnChanges, Input, Output, ViewChildren, EventEmitter, ViewChild, ElementRef, AfterViewInit, OnDestroy } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaTyoskentelypaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyoskentelypaikka-dto.model';
import { VardaPoissaoloDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-poissolo-dto.model';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import * as moment from 'moment';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { Observable, Subscription } from 'rxjs';
import { ErrorTree, HenkilostoErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from 'projects/virkailija-app/src/app/varda-main/services/varda-date.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { filter, distinctUntilChanged } from 'rxjs/operators';

@Component({
  selector: 'app-varda-poissaolo',
  templateUrl: './varda-poissaolo.component.html',
  styleUrls: [
    './varda-poissaolo.component.css',
    '../varda-palvelussuhde.component.css',
    '../../../varda-tyontekija-form.component.css'
  ]
})
export class VardaPoissaoloComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() palvelussuhde: VardaPalvelussuhdeDTO;
  @Input() poissaolo: VardaPoissaoloDTO;
  @Output() closePoissaolo = new EventEmitter<boolean>(true);
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  expandPanel: boolean;
  poissaoloForm: FormGroup;
  subscriptions: Array<Subscription> = [];
  i18n = VirkailijaTranslations;
  isEdit: boolean;

  poissaoloFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService = new HenkilostoErrorMessageService();

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private modalService: VardaModalService
  ) {
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
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (HenkilostoErrorMessageService.formIsValid(form)) {
      const poissaoloJson: VardaPoissaoloDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      if (this.poissaolo) {
        this.henkilostoService.updatePoissaolo(poissaoloJson).subscribe({
          next: poissaoloData => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      } else {
        this.henkilostoService.createPoissaolo(poissaoloJson).subscribe({
          next: poissaoloData => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      }

    }
  }

  deletePoissaolo(): void {
    this.henkilostoService.deletePoissaolo(parseInt(this.poissaolo.id)).subscribe({
      next: deleted => this.togglePanel(false, true),
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }

  togglePanel(open: boolean, refreshList?: boolean) {
    this.expandPanel = open;

    if (!open || refreshList) {
      this.disableForm();
      this.closePoissaolo?.emit(refreshList);
    }
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
}
