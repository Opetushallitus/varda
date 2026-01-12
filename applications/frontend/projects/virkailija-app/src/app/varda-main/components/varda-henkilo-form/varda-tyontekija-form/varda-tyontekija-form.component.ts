import { Component, Input, Output, EventEmitter, OnDestroy, OnInit } from '@angular/core';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkiloDTO, VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription, Observable, finalize } from 'rxjs';
import { TranslateService } from '@ngx-translate/core';
import { VardaKoosteApiService } from '../../../../core/services/varda-kooste-api.service';
import { TyontekijaKooste } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaUtilityService } from '../../../../core/services/varda-utility.service';


@Component({
    selector: 'app-varda-tyontekija-form',
    templateUrl: './varda-tyontekija-form.component.html',
    styleUrls: [
        '../varda-henkilo-form.component.css',
        './varda-tyontekija-form.component.css'
    ],
    standalone: false
})
export class VardaTyontekijaFormComponent implements OnInit, OnDestroy {
  @Input() henkilo: VardaHenkiloDTO;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() isEdit: boolean;
  @Output() valuesChanged: EventEmitter<boolean> = new EventEmitter<boolean>(true);

  i18n = VirkailijaTranslations;
  toimipaikkaAccess: UserAccess;
  tyontekijaFormErrors: Observable<Array<ErrorTree>>;
  deleteTyontekijaErrors: Observable<Array<ErrorTree>>;
  tyontekijaKooste: TyontekijaKooste;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isLoading = false;

  private errorService: VardaErrorMessageService;
  private deleteTyontekijaErrorService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService,
    private koosteService: VardaKoosteApiService,
    private modalService: VardaModalService,
    private snackBarService: VardaSnackBarService,
    private translateService: TranslateService,
    private utilityService: VardaUtilityService
  ) {
    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
    this.errorService = new VardaErrorMessageService(this.translateService);
    this.deleteTyontekijaErrorService = new VardaErrorMessageService(this.translateService);

    this.tyontekijaFormErrors = this.errorService.initErrorList();
    this.deleteTyontekijaErrors = this.deleteTyontekijaErrorService.initErrorList();

    this.subscriptions.push(
      this.modalService.getFormValuesChanged().subscribe(
        formValuesChanged => this.valuesChanged.emit(formValuesChanged)
      )
    );
  }

  ngOnInit() {
    this.henkilostoService.activeTyontekija.next(null);
    this.toimipaikkaAccess = this.authService.getUserAccess(this.henkilonToimipaikka?.organisaatio_oid);
    this.valuesChanged.emit(false);
    this.henkilostoService.initFormErrorList(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id, this.tyontekija);

    this.subscriptions.push(
      this.henkilostoService.listenHenkilostoListUpdate().subscribe(() =>
        this.henkilostoService.initFormErrorList(this.selectedVakajarjestaja.id, this.tyontekija))
    );
    this.getTyontekijaKooste();
  }

  getTyontekijaKooste() {
    if (this.tyontekija?.id) {
      this.isLoading = true;
      this.subscriptions.push(
        this.koosteService.getTyontekijaKooste(this.tyontekija.id, true).pipe(
          finalize(() => setTimeout(() => this.isLoading = false, 500))
        ).subscribe({
          next: result => {
            this.henkilostoService.activeTyontekija.next(result);
            this.tyontekijaKooste = result;
          },
          error: err => this.errorService.handleError(err, this.snackBarService)
        })
      );
    }
  }

  updateTyontekija(tyontekija: TyontekijaListDTO) {
    this.tyontekija = tyontekija;
    this.getTyontekijaKooste();
  }

  deleteTyontekija() {
    this.henkilostoService.deleteTyontekija(this.tyontekija.id).subscribe({
      next: () => {
        this.modalService.setModalCloseWithoutConfirmation(true);
        this.snackBarService.warning(this.i18n.tyontekija_delete_success);
        this.henkilostoService.sendHenkilostoListUpdate();
        this.modalService.setModalOpen(false);
      },
      error: err => this.deleteTyontekijaErrorService.handleError(err, this.snackBarService)
    });
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
    this.henkilostoService.activeTyontekija.next(null);
    this.utilityService.setFocusObjectSubject(null);
  }
}
