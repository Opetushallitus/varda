import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaTaydennyskoulutusDTO, VardaTaydennyskoulutusTyontekijaDTO, VardaTaydennyskoulutusTyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { BehaviorSubject, Observable } from 'rxjs';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import * as moment from 'moment';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from '../../../services/varda-date.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-varda-taydennyskoulutus-form',
  templateUrl: './varda-taydennyskoulutus-form.component.html',
  styleUrls: ['./varda-taydennyskoulutus-form.component.css', '../varda-taydennyskoulutus.component.css']
})
export class VardaTaydennyskoulutusFormComponent implements OnInit {
  @Input() taydennyskoulutus: VardaTaydennyskoulutusDTO;
  @Input() userAccess: UserAccess;
  @Output() refreshList = new EventEmitter<boolean>(true);
  currentOsallistujat: Array<VardaTaydennyskoulutusTyontekijaDTO> = [];
  tyontekijaList: Array<VardaTaydennyskoulutusTyontekijaListDTO>;
  i18n = VirkailijaTranslations;
  taydennyskoulutusForm: FormGroup;
  taydennyskoulutusFormErrors: Observable<Array<ErrorTree>>;
  isEdit: boolean;
  openTyontekijatBoolean: boolean;
  editFormBoolean: boolean;
  limitedEditAccess: boolean;
  firstAllowedDate = VardaDateService.henkilostoReleaseDate;
  isLoading = new BehaviorSubject<boolean>(false);
  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private snackBarService: VardaSnackBarService,
    private modalService: VardaModalService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService,
    private translateService: TranslateService
  ) {
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.taydennyskoulutusFormErrors = this.henkilostoErrorService.initErrorList();
  }

  ngOnInit() {
    this.listTyontekijat();
    this.initForm();
  }

  initForm() {
    this.taydennyskoulutusForm = new FormGroup({
      id: new FormControl(this.taydennyskoulutus?.id),
      lahdejarjestelma: new FormControl(this.taydennyskoulutus?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      nimi: new FormControl(this.taydennyskoulutus?.nimi, Validators.required),
      koulutuspaivia: new FormControl(this.taydennyskoulutus?.koulutuspaivia, [Validators.required, Validators.min(0.5), Validators.max(160), VardaFormValidators.remainderOf(0.5)]),
      suoritus_pvm: new FormControl(this.taydennyskoulutus ? moment(this.taydennyskoulutus?.suoritus_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
    });

    this.taydennyskoulutusForm.valueChanges.subscribe(() => {
      this.modalService.setFormValuesChanged(!this.taydennyskoulutusForm.pristine);
    });

    if (this.taydennyskoulutus?.taydennyskoulutus_tyontekijat) {
      this.currentOsallistujat = [...this.taydennyskoulutus?.taydennyskoulutus_tyontekijat];
      this.limitedEditAccess = this.taydennyskoulutus?.taydennyskoulutus_tyontekijat_count !== this.taydennyskoulutus?.taydennyskoulutus_tyontekijat.length;
    }

    if (!this.userAccess.taydennyskoulutustiedot.tallentaja || this.taydennyskoulutus?.id) {
      this.disableForm();
    } else {
      this.enableForm();
      this.openTyontekijatBoolean = true;
    }
  }


  saveTaydennyskoulutus(form: FormGroup) {
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form) && this.checkRoster()) {
      this.isLoading.next(true);
      const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
        ...form.value,
        suoritus_pvm: form.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      if (this.taydennyskoulutus?.id) {
        this.fillTyontekijat(taydennyskoulutusJson);

        this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: (taydennyskoulutusData) => {
            this.taydennyskoulutus = { ...this.taydennyskoulutus, ...taydennyskoulutusData };
            this.saveSuccess();
            this.initForm();
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => setTimeout(() => this.isLoading.next(false), 1500));
      } else {
        taydennyskoulutusJson.taydennyskoulutus_tyontekijat = [...this.currentOsallistujat];

        this.henkilostoService.createTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: (taydennyskoulutusData) => {
            this.taydennyskoulutus = taydennyskoulutusData;
            this.saveSuccess();
            this.initForm();
          },
          error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
        }).add(() => setTimeout(() => this.isLoading.next(false), 1500));
      }

    }
  }

  deleteTaydennyskoulutus(): void {
    this.henkilostoService.deleteTaydennyskoulutus(this.taydennyskoulutus.id).subscribe({
      next: deleted => {
        this.snackBarService.warning(this.i18n.taydennyskoulutus_delete_success);
        this.refreshList.emit();
        this.modalService.setFormValuesChanged(false);
        this.modalService.setModalOpen(false);

      },
      error: subErr => this.henkilostoErrorService.handleError(subErr, this.snackBarService)
    });
  }

  saveSuccess() {

    this.snackBarService.success(this.i18n.taydennyskoulutus_save_success);
    this.disableForm();
    this.taydennyskoulutusForm.markAsPristine();
    this.refreshList.emit();
    this.modalService.setFormValuesChanged(false);
  }

  disableForm() {
    this.isEdit = false;
    this.taydennyskoulutusForm.disable();
  }

  enableForm() {
    this.isEdit = true;
    this.taydennyskoulutusForm.enable();
  }


  selectOsallistujat(osallistujat: Array<VardaTaydennyskoulutusTyontekijaDTO>) {
    this.currentOsallistujat = osallistujat;
    if (JSON.stringify(osallistujat) !== JSON.stringify(this.taydennyskoulutus?.taydennyskoulutus_tyontekijat)) {
      this.taydennyskoulutusForm.markAsDirty();
      this.enableForm();
    }
  }

  listTyontekijat() {
    const osallistujaJson = {
      vakajarjestaja_oid: this.vakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid
    };

    this.henkilostoService.getTaydennyskoulutuksetTyontekijat(osallistujaJson).subscribe(tyontekijaList => {
      tyontekijaList.forEach(tyontekija => tyontekija.nimi = `${tyontekija.henkilo_sukunimi}, ${tyontekija.henkilo_etunimet}`);
      this.tyontekijaList = tyontekijaList;
    });
  }


  checkRoster(): boolean {
    const withoutNimike = this.currentOsallistujat.find(osallistuja => !osallistuja.tehtavanimike_koodi);
    if (withoutNimike) {
      const nimikePuuttuuError = {
        error: {
          UI: [{
            error_code: 'UI001',
            description: null,
            translations: [
              {
                language: this.translateService.currentLang.toLocaleUpperCase(),
                description: this.translateService.instant('backend.UI-001')
              }
            ]
          }]
        }
      };
      this.henkilostoErrorService.handleError(nimikePuuttuuError, this.snackBarService);
    }
    return !withoutNimike;
  }

  fillTyontekijat(taydennyskoulutusJson: VardaTaydennyskoulutusDTO): void {
    const toRemove = this.taydennyskoulutus.taydennyskoulutus_tyontekijat.filter(existingTyontekija =>
      !this.currentOsallistujat.find(
        osallistuja => osallistuja.henkilo_oid === existingTyontekija.henkilo_oid && osallistuja.tehtavanimike_koodi === existingTyontekija.tehtavanimike_koodi
      )
    ).map(existingTyontekija => ({
        tyontekija: existingTyontekija.tyontekija,
        tehtavanimike_koodi: existingTyontekija.tehtavanimike_koodi
      }));

    if (toRemove.length) {
      taydennyskoulutusJson.taydennyskoulutus_tyontekijat_remove = toRemove;
    }

    const toAdd = this.currentOsallistujat.filter(osallistuja =>
      !this.taydennyskoulutus.taydennyskoulutus_tyontekijat.find(
        existingTyontekija => osallistuja.henkilo_oid === existingTyontekija.henkilo_oid && osallistuja.tehtavanimike_koodi === existingTyontekija.tehtavanimike_koodi
      )
    );
    if (toAdd.length) {
      taydennyskoulutusJson.taydennyskoulutus_tyontekijat_add = toAdd;
    }
  }
}
