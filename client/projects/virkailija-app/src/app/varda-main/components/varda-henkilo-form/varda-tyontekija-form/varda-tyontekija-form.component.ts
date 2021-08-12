import { Component, OnChanges, Input, Output, EventEmitter, SimpleChanges, OnDestroy } from '@angular/core';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkiloDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription, Observable } from 'rxjs';
import { TranslateService } from '@ngx-translate/core';


@Component({
  selector: 'app-varda-tyontekija-form',
  templateUrl: './varda-tyontekija-form.component.html',
  styleUrls: [
    '../varda-henkilo-form.component.css',
    './varda-tyontekija-form.component.css'
  ]
})
export class VardaTyontekijaFormComponent implements OnChanges, OnDestroy {
  @Input() henkilo: VardaHenkiloDTO;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() isEdit: boolean;
  @Output() valuesChanged: EventEmitter<boolean> = new EventEmitter<boolean>(true);

  i18n = VirkailijaTranslations;
  subscriptions: Array<Subscription> = [];
  toimipaikkaAccess: UserAccess;
  henkilonTutkinnot: Array<VardaTutkintoDTO>;
  tyontekijaFormErrors: Observable<Array<ErrorTree>>;
  deleteTyontekijaErrors: Observable<Array<ErrorTree>>;

  private henkilostoErrorService: VardaErrorMessageService;
  private deleteTyontekijaErrorService: VardaErrorMessageService;

  constructor(
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService,
    private modalService: VardaModalService,
    private snackBarService: VardaSnackBarService,
    private translateService: TranslateService
  ) {
    this.henkilostoErrorService = new VardaErrorMessageService(this.translateService);
    this.deleteTyontekijaErrorService = new VardaErrorMessageService(this.translateService);

    this.tyontekijaFormErrors = this.henkilostoErrorService.initErrorList();
    this.deleteTyontekijaErrors = this.deleteTyontekijaErrorService.initErrorList();

    this.subscriptions.push(this.modalService.getFormValuesChanged().subscribe(formValuesChanged => this.valuesChanged.emit(formValuesChanged)));
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  ngOnChanges(changes: SimpleChanges) {
    this.toimipaikkaAccess = this.authService.getUserAccess(this.henkilonToimipaikka?.organisaatio_oid);
    this.valuesChanged.emit(false);

    this.henkilostoService.initFormErrorList(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id, this.tyontekija);
    this.subscriptions.push(
      this.henkilostoService.listenHenkilostoListUpdate().subscribe(() => this.henkilostoService.initFormErrorList(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().id, this.tyontekija))
    );
  }

  setTutkinnot(tutkinnot: Array<VardaTutkintoDTO>) {
    this.henkilonTutkinnot = tutkinnot;
  }

  updateTyontekija(tyontekija: TyontekijaListDTO) {
    this.tyontekija = tyontekija;
  }

  poistaTyontekija() {
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
}
