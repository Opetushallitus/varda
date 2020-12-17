import { Component, OnChanges, Input, Output, EventEmitter } from '@angular/core';
import { VardaHenkiloDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { HenkilostoErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaKoodistoService } from 'varda-shared';
import { KoodistoEnum, KoodistoSortBy, KoodistoDTO, CodeDTO } from 'projects/varda-shared/src/lib/dto/koodisto-models';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { TyontekijaListDTO, VardaTyontekijaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';



@Component({
  selector: 'app-varda-tyontekija-tutkinto',
  templateUrl: './varda-tyontekija-tutkinto.component.html',
  styleUrls: [
    './varda-tyontekija-tutkinto.component.css',
    '../varda-tyontekija-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaTyontekijaTutkintoComponent implements OnChanges {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilo: VardaHenkiloDTO;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Output() changeTutkinnot = new EventEmitter<Array<VardaTutkintoDTO>>(true);
  @Output() updateTyontekija = new EventEmitter<TyontekijaListDTO>(true);

  tutkintoFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService: HenkilostoErrorMessageService;
  i18n = VirkailijaTranslations;
  tutkintoViewLimit = 3;
  tutkintoOptions: Array<CodeDTO>;
  uusiTutkinto: any;
  henkilonTutkinnot: BehaviorSubject<Array<VardaTutkintoDTO>> = new BehaviorSubject<Array<VardaTutkintoDTO>>([]);
  henkilonTutkinnotExpand: boolean;
  addTutkinto: boolean;
  pendingTutkinto: boolean;
  isSubmitting = new BehaviorSubject<boolean>(false);

  tutkintoForm: FormGroup;

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService
  ) {
    this.henkilostoErrorService = new HenkilostoErrorMessageService(translateService);
    this.tutkintoFormErrors = this.henkilostoErrorService.initErrorList();
    this.henkilonTutkinnot.subscribe(tutkinnot => {
      this.changeTutkinnot.emit(tutkinnot);
    });
  }

  ngOnChanges() {
    if (this.toimipaikkaAccess.tyontekijatiedot.katselija) {
      this.getHenkilonTutkinnot();
    }
  }

  getHenkilonTutkinnot() {
    this.henkilostoErrorService.resetErrorList();
    this.initTutkintoForm();
    forkJoin([
      this.koodistoService.getKoodisto(KoodistoEnum.tutkinto, KoodistoSortBy.codeValue),
      this.henkilostoService.getTutkinnot(this.henkilo.henkilo_oid)
    ]).subscribe({
      next: ([tutkintoKoodisto, henkilonTutkinnot]) => {
        if (henkilonTutkinnot && tutkintoKoodisto) {
          this.tutkintoOptions = tutkintoKoodisto.codes.filter(koodisto => !henkilonTutkinnot.some(tutkinto => tutkinto.tutkinto_koodi === koodisto.code_value)).reverse();
          this.henkilonTutkinnot.next(this.fillTutkinnot(henkilonTutkinnot, tutkintoKoodisto));
          this.addTutkinto = !henkilonTutkinnot.length;
        }
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  fillTutkinnot(henkilonTutkinnot: Array<VardaTutkintoDTO>, tutkintoKoodisto: KoodistoDTO) {
    const existingTutkinnot = henkilonTutkinnot.map(henkilonTutkinto => {
      const foundKoodisto = tutkintoKoodisto.codes.find(tutkinto => tutkinto.code_value === henkilonTutkinto.tutkinto_koodi);
      return {
        ...henkilonTutkinto,
        tutkinto_koodi: foundKoodisto.code_value,
        tutkinto_nimi: foundKoodisto.name
      };
    });

    return existingTutkinnot;
  }

  createTutkinto(tutkintoFormGroup: FormGroup) {
    if (tutkintoFormGroup.valid) {
      this.isSubmitting.next(true);

      if (!this.tyontekija.id) {
        return this.createTyontekija();
      }

      this.henkilostoService.createTutkinto(tutkintoFormGroup.value).subscribe({
        next: () => {
          this.snackBarService.success(this.i18n.tutkinnot_save_success);
          this.getHenkilonTutkinnot();
        },
        error: err => this.henkilostoErrorService.handleError(err, null, tutkintoFormGroup)
      }).add(() => setTimeout(() => this.isSubmitting.next(false), 500));
    }
  }

  deleteTutkinto(tutkintoId: number) {
    this.henkilostoService.deleteTutkinto(tutkintoId).subscribe({
      next: data => {
        this.snackBarService.warning(this.i18n.tutkinnot_delete_success);
        this.getHenkilonTutkinnot();
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }


  initTutkintoForm() {
    this.tutkintoForm = new FormGroup({
      henkilo_oid: new FormControl(this.henkilo.henkilo_oid),
      toimipaikka_oid: new FormControl(this.henkilonToimipaikka?.organisaatio_oid),
      vakajarjestaja_oid: new FormControl(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid),
      tutkinto_koodi: new FormControl(null, Validators.required)
    });
  }


  createTyontekija() {

    const tyontekijaDTO: VardaTyontekijaDTO = {
      henkilo_oid: this.henkilo.henkilo_oid,
      vakajarjestaja_oid: this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid,
      toimipaikka_oid: this.henkilonToimipaikka?.organisaatio_oid,
      lahdejarjestelma: Lahdejarjestelma.kayttoliittyma
    };

    this.henkilostoService.createTyontekija(tyontekijaDTO).subscribe({
      next: tyontekijaData => {

        this.tyontekija = {
          id: tyontekijaData.id,
          url: tyontekijaData.url,
          henkilo_id: this.henkilo.id,
          henkilo_oid: this.henkilo.henkilo_oid,
          rooli: HenkiloRooliEnum.tyontekija,
          tyoskentelypaikat: []
        };

        this.snackBarService.success(this.i18n.tyontekija_save_success);
        this.henkilostoService.sendHenkilostoListUpdate();
        this.updateTyontekija.emit(this.tyontekija);
        this.createTutkinto(this.tutkintoForm);
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

}
