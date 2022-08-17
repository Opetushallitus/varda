import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges } from '@angular/core';
import { VardaHenkiloDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { finalize, Observable, of, Subscription, switchMap } from 'rxjs';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import {
  ErrorTree,
  VardaErrorMessageService
} from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaKoodistoService, CodeDTO, KoodistoEnum, KoodistoSortBy } from 'varda-shared';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import {
  TyontekijaListDTO,
  VardaTyontekijaDTO
} from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { filter, take } from 'rxjs/operators';
import { TyontekijaTutkinto } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { sortByName, sortByTutkintoKoodi } from '../../../../../utilities/helper-functions';

@Component({
  selector: 'app-varda-tyontekija-tutkinto',
  templateUrl: './varda-tyontekija-tutkinto.component.html',
  styleUrls: [
    './varda-tyontekija-tutkinto.component.css',
    '../varda-tyontekija-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaTyontekijaTutkintoComponent implements OnInit, OnChanges, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilo: VardaHenkiloDTO;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Output() updateTyontekija = new EventEmitter<TyontekijaListDTO>(true);

  i18n = VirkailijaTranslations;
  tutkintoFormErrors: Observable<Array<ErrorTree>>;
  tutkintoViewLimit = 3;
  tutkintoCodes: Array<CodeDTO> = [];
  tutkintoValuesSorted: Array<string> = [];
  tutkintoOptions: Array<CodeDTO>;
  tutkintoList: Array<TyontekijaTutkinto> = [];
  henkilonTutkinnotExpand: boolean;
  addTutkinto: boolean;
  KoodistoEnum = KoodistoEnum;
  isSubmitting = false;
  tutkintoForm: FormGroup;

  private tyontekijaExists: boolean;
  private henkilostoErrorService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService
  ) {
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.tutkintoFormErrors = this.henkilostoErrorService.initErrorList();
  }

  ngOnInit() {
    this.tutkintoForm = new FormGroup({
      henkilo_oid: new FormControl(this.henkilo.henkilo_oid),
      toimipaikka_oid: new FormControl(this.henkilonToimipaikka?.organisaatio_oid),
      vakajarjestaja_oid: new FormControl(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid),
      tutkinto_koodi: new FormControl(null, Validators.required)
    });

    this.subscriptions.push(
      this.koodistoService.getKoodisto(KoodistoEnum.tutkinto, KoodistoSortBy.name).subscribe(result => {
        this.tutkintoCodes = result.codes.sort(sortByName);
        this.tutkintoValuesSorted = this.tutkintoCodes.map(code => code.code_value);
        this.updateTutkintoOptions();
      }),
      this.henkilostoService.activeTyontekija.pipe(
        // Take only first non null value
        filter(result => !!result),
        take(1)
      ).subscribe(result => {
        this.tutkintoList = result.tutkinnot.sort((a, b) => sortByTutkintoKoodi(a, b, this.tutkintoValuesSorted));
        this.updateTutkintoOptions();
        this.addTutkinto = !this.tutkintoList.length;
      })
    );
  }

  ngOnChanges(changes: SimpleChanges) {
    this.tyontekijaExists = !!this.tyontekija.id;
    this.addTutkinto = !this.tyontekijaExists;
  }

  updateTutkintoOptions() {
    this.tutkintoOptions = this.tutkintoCodes.filter(code => !this.tutkintoList.some(
      tutkinto => tutkinto.tutkinto_koodi.toLowerCase() === code.code_value.toLowerCase()
    )).sort(sortByName);
  }

  createTutkinto(tutkintoFormGroup: FormGroup) {
    this.henkilostoErrorService.resetErrorList();
    if (tutkintoFormGroup.valid) {
      this.isSubmitting = true;

      let tyontekijaCreated = false;
      const tyontekijaObservable = !this.tyontekijaExists ? this.createTyontekija() : of(null);
      this.subscriptions.push(
        tyontekijaObservable.pipe(
          switchMap((result: VardaTyontekijaDTO) =>  {
            if (!this.tyontekijaExists && result) {
              // Tyontekija has been successfully created, parse tyontekija data
              tyontekijaCreated = true;
              this.tyontekija = {
                id: result.id,
                url: result.url,
                henkilo_id: this.henkilo.id,
                henkilo_oid: result.henkilo_oid,
                rooli: HenkiloRooliEnum.tyontekija,
                is_missing_data: true,
                tehtavanimikkeet: []
              };
              this.snackBarService.success(this.i18n.tyontekija_save_success);
              this.henkilostoService.sendHenkilostoListUpdate();
            }
            return this.henkilostoService.createTutkinto(tutkintoFormGroup.value);
          }),
          finalize(() => {
            if (!this.tyontekijaExists && tyontekijaCreated) {
              // Tyontekija has been successfully created, emit event to parent component
              this.updateTyontekija.emit(this.tyontekija);
            }
            setTimeout(() => this.isSubmitting = false, 500);
          })
        ).subscribe({
          next: result => {
            // Tutkinto has been successfully created
            this.snackBarService.success(this.i18n.tutkinnot_save_success);
            this.addTutkinto = false;

            this.tutkintoList = this.tutkintoList.filter(tutkinto => tutkinto.id !== result.id);
            this.tutkintoList.push(result);
            this.tutkintoList = this.tutkintoList.sort((a, b) => sortByTutkintoKoodi(a, b, this.tutkintoValuesSorted));
            this.henkilostoService.sendHenkilostoListUpdate();

            if (!tyontekijaCreated) {
              // If tyontekija was not created, update options and ActiveTyontekija
              // If tyontekija was created, kooste is fetched
              this.updateTutkintoOptions();
              this.updateActiveTyontekija();
            }
          },
          error: err => this.henkilostoErrorService.handleError(err, null, tutkintoFormGroup)
        })
      );
    }
  }

  deleteTutkinto(tutkintoId: number) {
    this.subscriptions.push(
      this.henkilostoService.deleteTutkinto(tutkintoId).subscribe({
        next: data => {
          this.snackBarService.warning(this.i18n.tutkinnot_delete_success);

          this.tutkintoList = this.tutkintoList.filter(tutkinto => tutkinto.id !== tutkintoId);
          this.henkilostoService.sendHenkilostoListUpdate();
          this.updateTutkintoOptions();
          this.updateActiveTyontekija();
        },
        error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
      })
    );
  }

  updateActiveTyontekija() {
    const activeTyontekija = this.henkilostoService.activeTyontekija.getValue();
    this.henkilostoService.activeTyontekija.next({...activeTyontekija, tutkinnot: this.tutkintoList});
    this.henkilostoService.tutkintoChanged.next(true);
  }

  createTyontekija() {
    const tyontekijaDTO = {
      henkilo_oid: this.henkilo.henkilo_oid,
      vakajarjestaja_oid: this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid,
      toimipaikka_oid: this.henkilonToimipaikka?.organisaatio_oid,
      lahdejarjestelma: Lahdejarjestelma.kayttoliittyma
    };

    return this.henkilostoService.createTyontekija(tyontekijaDTO);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
