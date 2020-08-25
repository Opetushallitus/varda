import { Component, OnInit, OnChanges, Input, Output, ViewChildren, EventEmitter, Inject, ViewChild, ElementRef, AfterViewInit, OnDestroy } from '@angular/core';
import { VardaHenkiloDTO, VardaToimipaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess, SaveAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaTyoskentelypaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyoskentelypaikka-dto.model';
import { FormGroup, Validators, FormControl } from '@angular/forms';
import * as moment from 'moment';
import { DOCUMENT } from '@angular/common';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaKoodistoService } from 'varda-shared';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/dto/koodisto-models';
import { HenkilostoErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { Observable, Subscription } from 'rxjs';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { MatExpansionPanelHeader } from '@angular/material/expansion';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from 'projects/virkailija-app/src/app/varda-main/services/varda-date.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { filter, distinctUntilChanged } from 'rxjs/operators';

@Component({
  selector: 'app-varda-tyoskentelypaikka',
  templateUrl: './varda-tyoskentelypaikka.component.html',
  styleUrls: [
    './varda-tyoskentelypaikka.component.css',
    '../varda-palvelussuhde.component.css',
    '../../../varda-tyontekija-form.component.css'
  ]
})
export class VardaTyoskentelypaikkaComponent implements OnInit, OnChanges, AfterViewInit, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() palvelussuhde: VardaPalvelussuhdeDTO;
  @Input() henkilo: VardaHenkiloDTO;
  @Input() tyoskentelypaikka: VardaTyoskentelypaikkaDTO;
  @Output() closeTyoskentelypaikka = new EventEmitter<boolean>(true);
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  toimijaAccess: UserAccess;
  i18n = VirkailijaTranslations;
  expandPanel: boolean;
  currentToimipaikka: VardaToimipaikkaDTO;
  tyoskentelypaikkaForm: FormGroup;
  subscriptions: Array<Subscription> = [];
  tehtavanimikkeet: KoodistoDTO;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  isEdit: boolean;

  palvelussuhdeFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService = new HenkilostoErrorMessageService();

  constructor(
    @Inject(DOCUMENT) private document,
    private authService: AuthService,
    private henkilostoService: VardaHenkilostoApiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private modalService: VardaModalService
  ) {
    this.toimijaAccess = this.authService.getUserAccess();
    this.palvelussuhdeFormErrors = this.henkilostoErrorService.initErrorList();
    this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike).subscribe(koodisto => this.tehtavanimikkeet = koodisto);
  }

  ngOnInit() {
    this.expandPanel = !this.tyoskentelypaikka;

    this.tyoskentelypaikkaForm = new FormGroup({
      id: new FormControl(this.tyoskentelypaikka?.id),
      lahdejarjestelma: new FormControl(this.tyoskentelypaikka?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      palvelussuhde: new FormControl(this.palvelussuhde.url),
      toimipaikka_oid: new FormControl(this.tyoskentelypaikka?.toimipaikka_oid || this.henkilonToimipaikka?.organisaatio_oid),
      kiertava_tyontekija_kytkin: new FormControl(this.tyoskentelypaikka?.kiertava_tyontekija_kytkin || false, Validators.required),
      alkamis_pvm: new FormControl(this.tyoskentelypaikka ? moment(this.tyoskentelypaikka?.alkamis_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
      paattymis_pvm: new FormControl(this.tyoskentelypaikka?.paattymis_pvm ? moment(this.tyoskentelypaikka?.paattymis_pvm, VardaDateService.vardaApiDateFormat) : null),
      tehtavanimike_koodi: new FormControl(this.tyoskentelypaikka?.tehtavanimike_koodi, Validators.required),
      kelpoisuus_kytkin: new FormControl(this.tyoskentelypaikka?.kelpoisuus_kytkin, Validators.required),
    });

    if (!this.toimipaikkaAccess.tyontekijatiedot.tallentaja || this.tyoskentelypaikka) {
      this.disableForm();
    } else {
      this.enableForm();
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngAfterViewInit() {
    if (!this.tyoskentelypaikka) {
      this.panelHeader?.focus();
    }

    this.subscriptions.push(
      this.tyoskentelypaikkaForm.statusChanges
        .pipe(filter(() => !this.tyoskentelypaikkaForm.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  ngOnChanges() {
    if (this.toimipaikkaAccess.tyontekijatiedot.tallentaja) {
      this.toimipaikat = this.authService.getAuthorizedToimipaikat(this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().tallentajaToimipaikat, SaveAccess.tyontekijatiedot);
      this.toimipaikat = this.toimipaikat.filter(toimipaikka => toimipaikka.organisaatio_oid);
    } else {
      this.toimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().allToimipaikat;
    }
  }


  SaveTyoskentelypaikka(form: FormGroup): void {
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (!form.valid) {
      if (form.controls.kiertava_tyontekija_kytkin.value) {
        form.controls.toimipaikka_oid = null;
      } else if (!form.controls.toimipaikka_oid.value) {
        form.controls.toimipaikka_oid.setErrors({ required: true });
      }

      HenkilostoErrorMessageService.formIsValid(form);
    } else {
      const tyoskentelypaikkaJson: VardaTyoskentelypaikkaDTO = {
        ...form.value,
        kiertava_tyontekija_kytkin: form.controls.kiertava_tyontekija_kytkin.value,
        alkamis_pvm: form.value.alkamis_pvm.format(VardaDateService.vardaApiDateFormat),
        paattymis_pvm: form.value.paattymis_pvm?.isValid() ? form.value.paattymis_pvm.format(VardaDateService.vardaApiDateFormat) : null
      };

      if (this.tyoskentelypaikka) {
        this.henkilostoService.updateTyoskentelypaikka(tyoskentelypaikkaJson).subscribe({
          next: () => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      } else {
        this.henkilostoService.createTyoskentelypaikka(tyoskentelypaikkaJson).subscribe({
          next: () => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      }
    }
  }

  togglePanel(open: boolean, refreshList?: boolean) {
    this.expandPanel = open;

    if (!open || refreshList) {
      this.disableForm();
      this.closeTyoskentelypaikka?.emit(refreshList);
      if (refreshList) {
        this.henkilostoService.sendHenkilostoListUpdate();
      }
    }
  }

  deleteTyoskentelypaikka(): void {
    this.henkilostoService.deleteTyoskentelypaikka(parseInt(this.tyoskentelypaikka.id)).subscribe({
      next: () => this.togglePanel(false, true),
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }


  disableForm() {
    this.isEdit = false;
    this.tyoskentelypaikkaForm.disable();

    this.modalService.setFormValuesChanged(false);
  }

  enableForm() {
    this.isEdit = true;
    this.tyoskentelypaikkaForm.enable();
    if (this.tyoskentelypaikka) {
      this.tyoskentelypaikkaForm.controls.kiertava_tyontekija_kytkin.disable();
      this.tyoskentelypaikkaForm.controls.toimipaikka_oid.disable();
    }
    if (!this.toimijaAccess.tyontekijatiedot.tallentaja) {
      this.tyoskentelypaikkaForm.controls.kiertava_tyontekija_kytkin.disable();
    }
  }
}
