import { Component, OnDestroy, OnInit } from '@angular/core';
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
import { VardaToimipaikkaMinimalDto } from '../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { filter } from 'rxjs/operators';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { AbstractPuutteellisetComponent } from './abstract-puutteelliset.component';

@Component({
    selector: 'app-varda-puutteelliset-tiedot',
    templateUrl: './varda-puutteelliset-tiedot.component.html',
    styleUrls: [
        './varda-puutteelliset-tiedot.component.css',
        '../varda-raportit.component.css'
    ],
    standalone: false
})
export class VardaPuutteellisetTiedotComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  activeHenkilo: TyontekijaListDTO | LapsiListDTO;
  activeToimipaikka: VardaToimipaikkaMinimalDto;
  activeLink: string;
  confirmedFormLeave = true;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  subscriptions: Array<Subscription> = [];
  childSubscriptions: Array<Subscription> = [];
  showLapset: boolean;
  showTyontekijat: boolean;
  showToimipaikat: boolean;
  showOrganisaatio: boolean;
  defaultRoute = '';
  allowedRoutes = [];

  protected readonly ModalEvent = ModalEvent;

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private modalService: VardaModalService,
    private router: Router,
    private route: ActivatedRoute,
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(
        () => this.setPage()
      ),
    );

    this.checkUserAccess();
  }

  ngOnInit() {
    this.subscriptions.push(this.modalService.getModalOpen().subscribe(open => {
      if (!open) {
        this.activeHenkilo = null;
        this.activeToimipaikka = null;
      }
    }));
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  openHenkilo(instance: LapsiListDTO | TyontekijaListDTO): void {
    this.activeHenkilo = instance;
  }

  openToimipaikka(instance: VardaToimipaikkaMinimalDto): void {
    this.activeToimipaikka = instance;
  }

  handleFormClose(event: ModalEvent) {
    if (event === ModalEvent.hidden) {
      this.activeHenkilo = null;
      this.activeToimipaikka = null;
      this.confirmedFormLeave = true;
    }
  }

  formValuesChanged(hasChanged: boolean): void {
    this.confirmedFormLeave = !hasChanged;
  }

  checkUserAccess() {
    this.toimijaAccess = this.authService.getUserAccess();

    if (this.toimijaAccess.raportit.katselija) {
      this.showOrganisaatio = true;
      this.defaultRoute = 'organisaatio';
      this.allowedRoutes.push('organisaatio');
    }

    if (
      this.toimijaAccess.raportit.katselija || this.toimijaAccess.lapsitiedot.katselija || this.toimijaAccess.tyontekijatiedot.katselija
    ) {
      this.showToimipaikat = true;
      this.defaultRoute = 'toimipaikat';
      this.allowedRoutes.push('toimipaikat');
    }

    if (this.toimijaAccess.raportit.katselija || this.toimijaAccess.lapsitiedot.katselija || this.toimijaAccess.huoltajatiedot.katselija) {
      this.showLapset = true;
      this.defaultRoute = this.defaultRoute || 'lapset';
      this.allowedRoutes.push('lapset');
    }

    if (this.toimijaAccess.raportit.katselija || this.toimijaAccess.tyontekijatiedot.katselija) {
      this.showTyontekijat = true;
      this.defaultRoute = this.defaultRoute || 'tyontekijat';
      this.allowedRoutes.push('tyontekijat');
    }

    this.setPage();
  }

  setPage() {
    this.activeLink = this.router.url.split('?').shift().split('/').pop();
    if (!this.allowedRoutes.includes(this.activeLink)) {
      this.router.navigate([this.defaultRoute], { relativeTo: this.route });
    }
  }

  onActivateChild(childComponent: AbstractPuutteellisetComponent<any, any>) {
    this.childSubscriptions.push(
      childComponent.openHenkiloForm.subscribe(value => this.openHenkilo(value)),
      childComponent.openToimipaikkaForm.subscribe(value => this.openToimipaikka(value))
    );
  }

  onDeactivateChild() {
    this.childSubscriptions.forEach(sub => sub.unsubscribe());
  }

}
