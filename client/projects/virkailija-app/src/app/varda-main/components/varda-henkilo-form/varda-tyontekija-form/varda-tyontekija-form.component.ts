import { Component, OnChanges, Input, Output, EventEmitter, SimpleChanges, OnDestroy } from '@angular/core';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { HenkilostoErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkiloDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { TyontekijaListDTO, VardaTyontekijaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
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
  private henkilostoErrorService: HenkilostoErrorMessageService;
  private deleteTyontekijaErrorService: HenkilostoErrorMessageService;
  subscriptions: Array<Subscription> = [];
  toimipaikkaAccess: UserAccess;
  henkilonTutkinnot: Array<VardaTutkintoDTO>;
  tyontekijaFormErrors: Observable<Array<ErrorTree>>;
  deleteTyontekijaErrors: Observable<Array<ErrorTree>>;

  constructor(
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService,
    private modalService: VardaModalService,
    private snackBarService: VardaSnackBarService,
    private translateService: TranslateService
  ) {
    this.henkilostoErrorService = new HenkilostoErrorMessageService(translateService);
    this.deleteTyontekijaErrorService = new HenkilostoErrorMessageService(translateService);

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

    if (!this.tyontekija.id) {
      this.luoTyontekija();
    }
  }

  setTutkinnot(tutkinnot: Array<VardaTutkintoDTO>) {
    this.henkilonTutkinnot = tutkinnot;
  }


  luoTyontekija() {

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
      },
      error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }


  poistaTyontekija() {

    this.henkilostoService.deleteTyontekija(this.tyontekija.id).subscribe({
      next: () => {
        this.snackBarService.warning(this.i18n.tyontekija_delete_success);
        this.henkilostoService.sendHenkilostoListUpdate();
        this.modalService.setModalOpen(false);
      },
      error: err => this.deleteTyontekijaErrorService.handleError(err, this.snackBarService)
    });
  }

}
