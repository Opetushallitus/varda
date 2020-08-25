import { Component, OnChanges, Input, Output, EventEmitter, SimpleChanges, OnDestroy } from '@angular/core';
import { VardaHenkiloDTO } from '../../../utilities/models';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaTutkintoDTO } from '../../../utilities/models/dto/varda-tutkinto-dto.model';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaHenkilostoApiService } from '../../../core/services/varda-henkilosto.service';
import { VardaTyontekijaDTO, TyontekijaListDTO } from '../../../utilities/models/dto/varda-tyontekija-dto.model';
import { HenkiloRooliEnum } from '../../../utilities/models/enums/henkilorooli.enum';
import { HenkilostoErrorMessageService, ErrorTree } from '../../../core/services/varda-henkilosto-error-message.service';
import { Observable, Subscription } from 'rxjs';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { Lahdejarjestelma } from '../../../utilities/models/enums/hallinnointijarjestelma';

@Component({
  selector: 'app-varda-tyontekija-form',
  templateUrl: './varda-tyontekija-form.component.html',
  styleUrls: ['./varda-tyontekija-form.component.css']
})
export class VardaTyontekijaFormComponent implements OnChanges, OnDestroy {
  @Input() henkilo: VardaHenkiloDTO;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() isEdit: boolean;
  @Output() valuesChanged: EventEmitter<boolean> = new EventEmitter<boolean>(true);


  i18n = VirkailijaTranslations;
  private henkilostoErrorService = new HenkilostoErrorMessageService();
  private deleteTyontekijaErrorService = new HenkilostoErrorMessageService();
  promptDeleteHenkilo = false;
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
  ) {
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

        this.henkilostoService.sendHenkilostoListUpdate();
      },
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }


  poistaTyontekija() {

    this.henkilostoService.deleteTyontekija(this.tyontekija.id).subscribe({
      next: () => {
        this.henkilostoService.sendHenkilostoListUpdate();
        this.modalService.setModalOpen(false);
      },
      error: err => this.deleteTyontekijaErrorService.handleError(err)
    });
  }

}
