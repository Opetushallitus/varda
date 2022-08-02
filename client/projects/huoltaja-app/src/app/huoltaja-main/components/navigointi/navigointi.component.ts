import { Component, OnDestroy } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { combineLatest, Subscription } from 'rxjs';
import { filter, take } from 'rxjs/operators';
import { LoginService, UserHuollettavaDTO, VardaUserDTO, VardaKayttajatyyppi } from 'varda-shared';
import { HuoltajaApiService } from '../../../services/huoltaja-api.service';
import { HuoltajaRoute } from '../../../utilities/models/enum/huoltaja-route.enum';


@Component({
  selector: 'app-navigointi',
  templateUrl: './navigointi.component.html',
  styleUrls: ['./navigointi.component.css']
})
export class NavigointiComponent implements OnDestroy {
  i18n = HuoltajaTranslations;
  huoltajaRoute = HuoltajaRoute;
  pageHeader: string;
  activeLink: HuoltajaRoute;
  showError = true;
  subscriptions: Array<Subscription> = [];
  henkilot: Array<UserHuollettavaDTO> = [];
  henkilo: UserHuollettavaDTO;
  kayttajatyyppi: string;

  VardaKayttajatyyppi = VardaKayttajatyyppi;

  availableTabs = {
    varhaiskasvatustiedot: false,
    huoltajatiedot: false,
    tyontekijatiedot: false
  };

  constructor(
    private router: Router,
    private loginService: LoginService,
    private huoltajaApiService: HuoltajaApiService
  ) {

    this.loginService.getCurrentUser().pipe(filter(Boolean), take(1)).subscribe((user: VardaUserDTO) => this.openVarda(user));
    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe((navigation: NavigationEnd) => {
        this.setPage(this.router.routerState.root);
      })
    );

    combineLatest([
      this.huoltajaApiService.getVarhaiskasvatustiedot(),
      this.huoltajaApiService.getHuoltajatiedot(),
      this.huoltajaApiService.getTyontekijatiedot()
    ]).subscribe(([
      varhaiskasvatustiedot,
      huoltajatiedot,
      tyontekijatiedot
    ]) => {
      this.availableTabs.varhaiskasvatustiedot = !!varhaiskasvatustiedot?.lapset;
      this.availableTabs.huoltajatiedot = !!huoltajatiedot?.huoltajuussuhteet;
      this.availableTabs.tyontekijatiedot = !!tyontekijatiedot?.tyontekijat;
    });

    this.setPage(this.router.routerState.root);
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }

  openVarda(user: VardaUserDTO) {
    const userAsHuollettavaDTO: UserHuollettavaDTO = {
      etunimet: user?.etunimet,
      kutsumanimi: user?.kutsumanimi,
      sukunimi: user?.sukunimi,
      henkilo_oid: user?.henkilo_oid
    };

    this.kayttajatyyppi = user.kayttajatyyppi;

    this.henkilot = [userAsHuollettavaDTO, ...user.huollettava_list || []];
    this.henkilo = this.henkilot[this.henkilot.length - 1];
    this.huoltajaApiService.setHenkilot(this.henkilot);
    this.changeHenkilo(this.henkilo);
  }

  setPage(route: ActivatedRoute) {
    const urlPart = this.router.url.split('?').shift().split('/')[1];
    this.activeLink = HuoltajaRoute[urlPart];

    let snapshot = route.snapshot;
    while (snapshot) {
      this.pageHeader = snapshot.data.title || this.pageHeader;
      snapshot = snapshot.firstChild;
    }
  }

  changeHenkilo(henkilo: UserHuollettavaDTO) {
    this.huoltajaApiService.getRoute(this.henkilo?.henkilo_oid).subscribe(route => {
      this.router.navigate([route]);
    });
  }
}
