import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { ModalEvent } from 'projects/virkailija-app/src/app/shared/components/varda-modal-form/varda-modal-form.component';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription } from 'rxjs';

type HenkiloSection = 'lapset' | 'tyontekijat';

@Component({
  selector: 'app-varda-puutteelliset-tiedot',
  templateUrl: './varda-puutteelliset-tiedot.component.html',
  styleUrls: [
    './varda-puutteelliset-tiedot.component.css',
    '../varda-raportit.component.css'
  ]
})
export class VardaPuutteellisetTiedotComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  activeSuhde: TyontekijaListDTO | LapsiListDTO;
  activeSection: HenkiloSection;
  confirmedHenkiloFormLeave = true;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  subscriptions: Array<Subscription> = [];
  showLapset: boolean;
  showTyontekijat: boolean;
  defaultFragment: HenkiloSection;
  allowedFragments: Array<HenkiloSection> = [];

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private modalService: VardaModalService,
    private route: ActivatedRoute,
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.checkUserAccess();

    this.route.fragment.subscribe((fragment: HenkiloSection) =>
      this.activeSection = this.allowedFragments.includes(fragment) ? fragment : this.defaultFragment
    );

    this.checkUserAccess();
  }


  ngOnInit() {
    this.subscriptions.push(this.modalService.getModalOpen().subscribe(open => {
      if (!open) {
        this.activeSuhde = null;
      }
    }));
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  openHenkilo(suhde: LapsiListDTO | TyontekijaListDTO): void {
    this.activeSuhde = suhde;
  }

  handleFormClose(event: ModalEvent) {
    if (event === ModalEvent.hidden) {
      this.activeSuhde = null;
      this.confirmedHenkiloFormLeave = true;
    }
  }

  henkiloFormValuesChanged(hasChanged: boolean): void {
    this.confirmedHenkiloFormLeave = !hasChanged;
  }

  checkUserAccess() {
    this.toimijaAccess = this.authService.getUserAccess();
    if (this.toimijaAccess.raportit.katselija || this.toimijaAccess.lapsitiedot.katselija || this.toimijaAccess.huoltajatiedot.katselija) {
      this.showLapset = true;
      this.defaultFragment = 'lapset';
      this.allowedFragments.push('lapset');
    }

    if (this.toimijaAccess.raportit.katselija || this.toimijaAccess.tyontekijatiedot.katselija) {
      this.showTyontekijat = true;
      this.defaultFragment = this.defaultFragment || 'tyontekijat';
      this.allowedFragments.push('tyontekijat');
    }
  }
}
