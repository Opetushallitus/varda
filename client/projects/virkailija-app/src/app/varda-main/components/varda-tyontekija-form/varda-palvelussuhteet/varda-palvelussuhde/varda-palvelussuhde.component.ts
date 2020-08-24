import { Component, OnInit, OnChanges, Input, Output, ViewChildren, EventEmitter, ElementRef, OnDestroy } from '@angular/core';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaTyoskentelypaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyoskentelypaikka-dto.model';
import { VardaPoissaoloDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-poissolo-dto.model';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import * as moment from 'moment';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { Observable, Subscription } from 'rxjs';
import { HenkilostoErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaKoodistoService } from 'varda-shared';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/dto/koodisto-models';
import { VardaDateService } from '../../../../services/varda-date.service';

@Component({
  selector: 'app-varda-palvelussuhde',
  templateUrl: './varda-palvelussuhde.component.html',
  styleUrls: [
    './varda-palvelussuhde.component.css',
    '../varda-palvelussuhteet.component.css',
    '../../varda-tyontekija-form.component.css'
  ]
})
export class VardaPalvelussuhdeComponent implements OnInit, OnChanges, OnDestroy {
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() palvelussuhde: VardaPalvelussuhdeDTO;
  @Input() henkilonTutkinnot: Array<VardaTutkintoDTO>;
  @Output() closeAddPalvelussuhde = new EventEmitter<boolean>(true);
  @Output() changedPalvelussuhde = new EventEmitter<boolean>(true);
  i18n = VirkailijaTranslations;
  element: ElementRef;
  expandPanel: boolean;
  tyoskentelypaikat: Array<VardaTyoskentelypaikkaDTO>;
  poissaolot: Array<VardaPoissaoloDTO>;
  isEdit: boolean;
  addTyoskentelypaikkaBoolean: boolean;
  addPoissaoloBoolean: boolean;
  palvelussuhdeForm: FormGroup;
  palvelussuhdeFormErrors: Observable<Array<ErrorTree>>;
  subscriptions: Array<Subscription> = [];
  tyosuhdeKoodisto: KoodistoDTO;
  tyoaikaKoodisto: KoodistoDTO;
  private henkilostoErrorService = new HenkilostoErrorMessageService();
  constructor(
    private el: ElementRef,
    private henkilostoService: VardaHenkilostoApiService,
    private modalService: VardaModalService,
    private koodistoService: VardaKoodistoService
  ) {
    this.element = this.el;
    this.palvelussuhdeFormErrors = this.henkilostoErrorService.initErrorList();

    this.koodistoService.getKoodisto(KoodistoEnum.tyosuhde).subscribe(koodisto => this.tyosuhdeKoodisto = koodisto);
    this.koodistoService.getKoodisto(KoodistoEnum.tyoaika).subscribe(koodisto => this.tyoaikaKoodisto = koodisto);
  }


  ngOnInit() {
    const oletustutkinto = this.henkilonTutkinnot.length === 1 ? this.henkilonTutkinnot[0].tutkinto_koodi : null;
    this.palvelussuhdeForm = new FormGroup({
      id: new FormControl(this.palvelussuhde?.id),
      lahdejarjestelma: new FormControl(this.palvelussuhde?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      tyontekija: new FormControl(this.palvelussuhde?.tyontekija || `/api/henkilosto/v1/tyontekijat/${this.tyontekija.id}/`),
      toimipaikka_oid: new FormControl(this.palvelussuhde ? null : this.henkilonToimipaikka?.organisaatio_oid),
      alkamis_pvm: new FormControl(this.palvelussuhde ? moment(this.palvelussuhde?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.palvelussuhde?.paattymis_pvm ? moment(this.palvelussuhde?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      tyoaika_koodi: new FormControl(this.palvelussuhde?.tyoaika_koodi, Validators.required),
      tyosuhde_koodi: new FormControl(this.palvelussuhde?.tyosuhde_koodi, Validators.required),
      tyoaika_viikossa: new FormControl(this.palvelussuhde?.tyoaika_viikossa, [Validators.pattern('^\\d+([,.]\\d{1,2})?$'), Validators.max(50), Validators.required]),
      tutkinto_koodi: new FormControl(this.palvelussuhde?.tutkinto_koodi || oletustutkinto, Validators.required),
    });

    if (!this.toimipaikkaAccess.tyontekijatiedot.tallentaja || this.palvelussuhde) {
      this.disableForm();
    } else {
      this.enableForm();
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngOnChanges() {
    if (this.palvelussuhde) {
      this.getTyoskentelypaikat();
      this.getPoissaolot();
    } else {
      this.togglePanel(true);
    }
  }

  savePalvelussuhde(form: FormGroup): void {
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (HenkilostoErrorMessageService.formIsValid(form)) {
      const palvelussuhdeDTO: VardaPalvelussuhdeDTO = {
        ...form.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (this.palvelussuhde) {
        this.henkilostoService.updatePalvelussuhde(palvelussuhdeDTO).subscribe({
          next: palvelussuhdeData => this.changedPalvelussuhde.emit(),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      } else {
        this.henkilostoService.createPalvelussuhde(palvelussuhdeDTO).subscribe({
          next: palvelussuhdeData => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      }

    }
  }

  togglePanel(open: boolean, refreshList?: boolean) {
    this.expandPanel = open;

    if (!open || refreshList) {
      this.disableForm();
      this.closeAddPalvelussuhde?.emit(refreshList);
    }
  }

  closePoissaolo(refresh?: boolean): void {
    this.addPoissaoloBoolean = false;
    if (refresh) {
      this.getPoissaolot();
    }
  }

  getPoissaolot(): void {
    this.henkilostoService.getPoissaolot(parseInt(this.palvelussuhde.id)).subscribe({
      next: poissaoloData => this.poissaolot = poissaoloData,
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }

  deletePalvelussuhde(): void {
    this.henkilostoService.deletePalvelussuhde(parseInt(this.palvelussuhde.id)).subscribe({
      next: deleted => this.togglePanel(false, true),
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }

  getTyoskentelypaikat(): void {
    this.henkilostoService.getTyoskentelypaikat(parseInt(this.palvelussuhde.id)).subscribe({
      next: tyoskentelypaikkaData => this.tyoskentelypaikat = tyoskentelypaikkaData,
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }

  closeTyoskentelypaikka(refresh?: boolean): void {
    this.addTyoskentelypaikkaBoolean = false;
    if (refresh) {
      this.getTyoskentelypaikat();
    }
  }

  disableForm() {
    this.isEdit = false;
    this.palvelussuhdeForm.disable();
    this.modalService.setFormValuesChanged(false);
  }

  enableForm() {
    this.isEdit = true;
    this.palvelussuhdeForm.enable();
  }

}
