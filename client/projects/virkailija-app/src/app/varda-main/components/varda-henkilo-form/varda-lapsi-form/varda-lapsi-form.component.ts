import { Component, OnDestroy, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatRadioChange } from '@angular/material/radio';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaApiService } from 'projects/virkailija-app/src/app/core/services/varda-api.service';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaPaosApiService } from 'projects/virkailija-app/src/app/core/services/varda-paos-api.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkiloDTO, VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { LapsiListDTO, VardaLapsiDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription, Observable, BehaviorSubject, finalize } from 'rxjs';
import { filter } from 'rxjs/operators';
import { TranslateService } from '@ngx-translate/core';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaKoosteApiService } from '../../../../core/services/varda-kooste-api.service';
import { LapsiKooste } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaUtilityService } from '../../../../core/services/varda-utility.service';


@Component({
  selector: 'app-varda-lapsi-form',
  templateUrl: './varda-lapsi-form.component.html',
  styleUrls: [
    '../varda-henkilo-form.component.css',
    './varda-lapsi-form.component.css'
  ]
})
export class VardaLapsiFormComponent implements OnInit, OnDestroy {
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
  toimipaikkaAccess: UserAccess;
  lapsiFormErrors: Observable<Array<ErrorTree>>;
  deleteLapsiErrors: Observable<Array<ErrorTree>>;
  isSubmitting = false;
  deletePermission: boolean;
  lapsiKooste: LapsiKooste;

  private errorMessageService: VardaErrorMessageService;
  private deleteErrorMessageService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private paosService: VardaPaosApiService,
    private lapsiService: VardaLapsiService,
    private modalService: VardaModalService,
    private snackBarService: VardaSnackBarService,
    private koosteService: VardaKoosteApiService,
    private utilityService: VardaUtilityService,
    translateService: TranslateService
  ) {
    this.errorMessageService = new VardaErrorMessageService(translateService);
    this.deleteErrorMessageService = new VardaErrorMessageService(translateService);

    this.lapsiFormErrors = this.errorMessageService.initErrorList();
    this.deleteLapsiErrors = this.deleteErrorMessageService.initErrorList();

    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
    this.subscriptions.push(this.modalService.getFormValuesChanged().subscribe(formValuesChanged => this.valuesChanged.emit(formValuesChanged)));
  }

  ngOnInit() {
    this.lapsiService.activeLapsi.next(null);
    this.toimipaikkaAccess = this.authService.getUserAccess(this.henkilonToimipaikka?.organisaatio_oid);
    this.valuesChanged.emit(false);
    this.lapsiService.initFormErrorList(this.selectedVakajarjestaja.id, this.lapsi);

    if (!this.lapsi?.id) {
      this.initLapsiForm();
    } else {
      this.getLapsiKooste();
      this.setDeletePermission();
    }

    this.subscriptions.push(this.lapsiService.listenLapsiListUpdate().subscribe(() =>
      this.lapsiService.initFormErrorList(this.selectedVakajarjestaja.id, this.lapsi)));
  }

  initLapsiForm() {
    this.lapsiForm = new FormGroup({
      lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma),
      toimipaikka_oid: new FormControl(this.henkilonToimipaikka?.organisaatio_oid),
      henkilo_oid: new FormControl(this.henkilo.henkilo_oid, Validators.required),
      paos_jarjestaja_toimipaikka: new FormControl(null),
      paos_kytkin: new FormControl(false),
      vakatoimija: new FormControl(this.selectedVakajarjestaja.url),
      oma_organisaatio: new FormControl(null),
      paos_organisaatio: new FormControl(null),
    });

    this.paosToimipaikat = this.vardaVakajarjestajaService.getFilteredToimipaikat().tallentajaToimipaikat
      .filter(toimipaikat => toimipaikat.organisaatio_oid);

    this.subscriptions.push(
      this.lapsiForm.get('paos_jarjestaja_toimipaikka').valueChanges.pipe(filter(Boolean)).subscribe((toimipaikkaId: string) => {
        this.selectedToimipaikka = this.paosToimipaikat.find(toimipaikka => parseInt(toimipaikkaId, 10) === toimipaikka.id);
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

  fetchPaosJarjestajat(toimipaikkaId: number) {
    this.lapsiForm.get('oma_organisaatio').setValue(null);

    this.subscriptions.push(
      this.paosService.getPaosJarjestajat(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id, toimipaikkaId)
        .subscribe({
          next: paosJarjestajaData => this.paosJarjestajaKunnat$.next(paosJarjestajaData),
          error: err => this.errorMessageService.handleError(err, this.snackBarService),
        })
    );
  }

  createLapsi(form: FormGroup) {
    form.markAllAsTouched();
    this.errorMessageService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      const vardaCreateLapsiDTO: VardaLapsiDTO = {
        ...form.value
      };
      this.isSubmitting = true;

      this.subscriptions.push(
        this.lapsiService.createLapsi(vardaCreateLapsiDTO).pipe(
          finalize(() => setTimeout(() => this.isSubmitting = false, 500))
        ).subscribe({
          next: lapsiData => {
            this.snackBarService.success(this.i18n.lapsi_save_success);
            this.lapsiService.sendLapsiListUpdate();

            this.lapsi = this.createLapsiListDTO(lapsiData);
            this.getLapsiKooste();
            this.setDeletePermission();
          },
          error: err => this.errorMessageService.handleError(err, this.snackBarService)
        })
      );
    }
  }

  deleteLapsi() {
    this.subscriptions.push(
      this.lapsiService.deleteLapsi(this.lapsi.id).subscribe({
        next: () => {
          this.modalService.setModalCloseWithoutConfirmation(true);
          this.lapsiService.sendLapsiListUpdate();
          this.modalService.setModalOpen(false);
          this.snackBarService.warning(this.i18n.lapsi_delete_success);
        },
        error: err => this.deleteErrorMessageService.handleError(err, this.snackBarService)
      })
    );
  }

  createLapsiListDTO(lapsiDTO: VardaLapsiDTO): LapsiListDTO {
    const henkiloID = lapsiDTO.henkilo.split('/').filter(Boolean).pop();
    return {
      id: lapsiDTO.id,
      url: lapsiDTO.url,
      henkilo_id: parseInt(henkiloID, 10),
      henkilo_oid: lapsiDTO.henkilo_oid,
      rooli: HenkiloRooliEnum.lapsi,
      etunimet: this.henkilo.etunimet,
      sukunimi: this.henkilo.sukunimi,
      vakatoimija_oid: lapsiDTO.vakatoimija_oid,
      vakatoimija_nimi: null,
      oma_organisaatio_oid: lapsiDTO.oma_organisaatio_oid,
      oma_organisaatio_nimi: lapsiDTO.oma_organisaatio_nimi,
      paos_organisaatio_oid: lapsiDTO.paos_organisaatio_oid,
      paos_organisaatio_nimi: lapsiDTO.paos_organisaatio_nimi,
      tallentaja_organisaatio_oid: lapsiDTO.oma_organisaatio_oid ? this.selectedVakajarjestaja.organisaatio_oid : null,
      toimipaikat: [],
    };
  }

  getLapsiKooste() {
    if (this.lapsi?.id) {
      this.subscriptions.push(
        this.koosteService.getLapsiKooste(this.lapsi.id).subscribe({
          next: result => {
            this.lapsiService.activeLapsi.next(result);
            this.lapsiKooste = result;
          },
          error: err => this.errorMessageService.handleError(err, this.snackBarService)
        })
      );
    }
  }

  setDeletePermission() {
    this.deletePermission = !!this.toimipaikkaAccess.lapsitiedot.tallentaja;
    if (this.lapsi.paos_organisaatio_oid && this.lapsi.tallentaja_organisaatio_oid !== this.selectedVakajarjestaja.organisaatio_oid) {
      this.deletePermission = false;
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
    this.lapsiService.activeLapsi.next(null);
    this.utilityService.setFocusObjectSubject(null);
  }
}
