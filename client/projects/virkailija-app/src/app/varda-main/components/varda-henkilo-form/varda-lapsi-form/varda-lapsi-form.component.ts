import { Component, OnChanges, OnDestroy, Input, Output, SimpleChanges, EventEmitter } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatRadioChange } from '@angular/material/radio';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaApiWrapperService } from 'projects/virkailija-app/src/app/core/services/varda-api-wrapper.service';
import { VardaApiService } from 'projects/virkailija-app/src/app/core/services/varda-api.service';
import { HenkilostoErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaPaosApiService } from 'projects/virkailija-app/src/app/core/services/varda-paos-api.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkiloDTO, VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { LapsiListDTO, VardaLapsiDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription, Observable, BehaviorSubject } from 'rxjs';
import { filter } from 'rxjs/operators';
import { TranslateService } from '@ngx-translate/core';


@Component({
  selector: 'app-varda-lapsi-form',
  templateUrl: './varda-lapsi-form.component.html',
  styleUrls: [
    '../varda-henkilo-form.component.css',
    './varda-lapsi-form.component.css'
  ]
})
export class VardaLapsiFormComponent implements OnChanges, OnDestroy {
  @Input() henkilo: VardaHenkiloDTO;
  @Input() lapsi: LapsiListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() isEdit: boolean;
  @Output() valuesChanged: EventEmitter<boolean> = new EventEmitter<boolean>(true);


  i18n = VirkailijaTranslations;

  lapsiForm: FormGroup;
  paosToimipaikat: Array<VardaToimipaikkaMinimalDto>;
  paosJarjestajaKunnat$ = new BehaviorSubject<Array<VardaVakajarjestajaUi>>(null);
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;

  private lapsiErrorService: HenkilostoErrorMessageService;
  private deleteLapsiErrorService: HenkilostoErrorMessageService;
  subscriptions: Array<Subscription> = [];
  toimipaikkaAccess: UserAccess;
  henkilonTutkinnot: Array<VardaTutkintoDTO>;
  lapsiFormErrors: Observable<Array<ErrorTree>>;
  deleteLapsiErrors: Observable<Array<ErrorTree>>;
  isSubmitting = new BehaviorSubject<boolean>(false);

  constructor(
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private paosService: VardaPaosApiService,
    private lapsiService: VardaLapsiService,
    private modalService: VardaModalService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService
  ) {
    this.lapsiErrorService = new HenkilostoErrorMessageService(translateService);
    this.deleteLapsiErrorService = new HenkilostoErrorMessageService(translateService);

    this.lapsiFormErrors = this.lapsiErrorService.initErrorList();
    this.deleteLapsiErrors = this.deleteLapsiErrorService.initErrorList();

    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
    this.subscriptions.push(this.modalService.getFormValuesChanged().subscribe(formValuesChanged => this.valuesChanged.emit(formValuesChanged)));
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  ngOnChanges(changes: SimpleChanges) {
    this.toimipaikkaAccess = this.authService.getUserAccess(this.henkilonToimipaikka?.organisaatio_oid);
    this.valuesChanged.emit(false);

    if (!this.lapsi.id) {
      this.initLapsiForm();
    }
  }

  initLapsiForm() {
    this.lapsiForm = new FormGroup({
      henkilo_oid: new FormControl(this.henkilo.henkilo_oid, Validators.required),
      paos_jarjestaja_toimipaikka: new FormControl(null),
      paos_kytkin: new FormControl(false),
      vakatoimija: new FormControl(this.selectedVakajarjestaja.url),
      oma_organisaatio: new FormControl(null),
      lp_organisaatio: new FormControl(null),
      paos_organisaatio: new FormControl(null),
    });

    this.paosToimipaikat = this.vardaVakajarjestajaService.getFilteredToimipaikat().tallentajaToimipaikat
      .filter(toimipaikat => toimipaikat.organisaatio_oid);

    this.subscriptions.push(
      this.lapsiForm.get('paos_jarjestaja_toimipaikka').valueChanges.pipe(filter(Boolean)).subscribe((toimipaikkaId: string) => {
        this.selectedToimipaikka = this.paosToimipaikat.find(toimipaikka => parseInt(toimipaikkaId) === toimipaikka.id);
        if (this.selectedToimipaikka) {
          this.fetchPaosJarjestajat(this.selectedToimipaikka?.id);
        }
      })
    );
  }

  changePaosKytkin(change: MatRadioChange) {
    if (change.value) {
      this.lapsiForm.get('vakatoimija').setValue(null);
      this.lapsiForm.get('paos_jarjestaja_toimipaikka').setValue(this.henkilonToimipaikka?.id || null);
      this.lapsiForm.get('oma_organisaatio').setValidators(Validators.required);
    } else {
      this.lapsiForm.get('vakatoimija').setValue(this.selectedVakajarjestaja.url);
      this.lapsiForm.get('paos_organisaatio').setValue(null);
      this.lapsiForm.get('oma_organisaatio').setValue(null);
      this.lapsiForm.get('oma_organisaatio').clearValidators();
    }

    this.lapsiForm.get('oma_organisaatio').updateValueAndValidity();
  }

  fetchPaosJarjestajat(toimipaikkaId: number) {
    this.lapsiForm.get('oma_organisaatio').setValue(null);

    this.paosService.getPaosJarjestajat(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id, toimipaikkaId)
      .subscribe({
        next: paosJarjestajaData => this.paosJarjestajaKunnat$.next(paosJarjestajaData),
        error: err => this.lapsiErrorService.handleError(err, this.snackBarService),
      });
  }

  changePaosOrganisaatio(omaOrganisaatioUrl?: string) {
    const vakajarjestajaOrganisaatioUrl = VardaApiService.getVakajarjestajaUrlFromId(this.selectedVakajarjestaja.id);
    if (omaOrganisaatioUrl.endsWith(vakajarjestajaOrganisaatioUrl)) {
      this.lapsiForm.get('paos_organisaatio').setValue(this.selectedToimipaikka.paos_organisaatio_url);
    } else {
      this.lapsiForm.get('paos_organisaatio').setValue(vakajarjestajaOrganisaatioUrl);
    }
    this.lapsiForm.get('vakatoimija').setValue(null);
    this.lapsiForm.get('oma_organisaatio').setValue(omaOrganisaatioUrl);
  }

  luoLapsi(form: FormGroup) {
    form.markAllAsTouched();
    this.lapsiErrorService.resetErrorList();

    if (HenkilostoErrorMessageService.formIsValid(form)) {
      const vardaCreateLapsiDTO: VardaLapsiDTO = {
        ...form.value
      };
      this.isSubmitting.next(true);

      this.lapsiService.createLapsi(vardaCreateLapsiDTO).subscribe({
        next: lapsiData => {
          this.snackBarService.success(this.i18n.lapsi_save_success);
          this.lapsiService.sendLapsiListUpdate();

          this.lapsiService.getVakajarjestajaLapset(this.selectedVakajarjestaja.id, { search: lapsiData.henkilo_oid }).subscribe({
            next: henkiloListData => {
              const foundHenkilo = henkiloListData.results.find(henkilo => henkilo.henkilo_oid === lapsiData.henkilo_oid);
              const foundLapsi = foundHenkilo.lapset.find(lapsi => lapsi.id === lapsiData.id);
              this.lapsi = foundLapsi;
            },
            error: (err) => console.error(err)
          });
        },
        error: err => this.lapsiErrorService.handleError(err, this.snackBarService)
      }).add(() => setTimeout(() => this.isSubmitting.next(false), 500));
    }

  }

  poistaLapsi() {
    this.lapsiService.deleteLapsi(this.lapsi.id).subscribe({
      next: () => {
        this.lapsiService.sendLapsiListUpdate();
        this.modalService.setModalOpen(false);
        this.snackBarService.warning(this.i18n.lapsi_delete_success);
      },
      error: err => this.deleteLapsiErrorService.handleError(err, this.snackBarService)
    });
  }

}
