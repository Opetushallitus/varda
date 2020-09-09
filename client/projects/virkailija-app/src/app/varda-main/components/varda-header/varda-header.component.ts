import { AfterViewInit, ChangeDetectorRef, Component, Input, OnInit } from '@angular/core';
import { AuthService } from '../../../core/auth/auth.service';
import { NavigationEnd, Router, ActivatedRoute } from '@angular/router';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaKayttooikeusRoles, VardaVakajarjestajaUi } from '../../../utilities/models';
import { environment } from '../../../../environments/environment';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { LoginService } from 'varda-shared';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { filter } from 'rxjs/operators';

declare var $: any;

@Component({
  selector: 'app-varda-header',
  templateUrl: './varda-header.component.html',
  styleUrls: ['./varda-header.component.css']
})
export class VardaHeaderComponent implements OnInit {

  @Input() isDashboardPage: boolean;
  toimipaikkaSelected: boolean;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  vakajarjestajat: Array<VardaVakajarjestajaUi>;
  activeNavItem: string;
  virkailijaRaamit: boolean;

  tilapainenHenkilostoOnlyBoolean: boolean;
  toimipaikkaAccessIfAnyToimipaikka: UserAccess;

  constructor(
    private authService: AuthService,
    private loginService: LoginService,
    private activatedRoute: ActivatedRoute,
    private router: Router,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaUtilityService: VardaUtilityService
  ) {
    this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe((navigationEnd) => {
      let topRoute = this.activatedRoute.firstChild;
      while (topRoute.firstChild) {
        topRoute = topRoute.firstChild;
      }

      this.activeNavItem = topRoute.snapshot?.data?.nav_item || topRoute.snapshot.routeConfig.path;
    });

    this.vardaVakajarjestajaService.getSelectedVakajarjestajaObs().subscribe((data) => {
      this.selectedVakajarjestaja = data.vakajarjestaja;
    });

    this.vardaVakajarjestajaService.getVakajarjestajatObs().subscribe(() => {
      this.vakajarjestajat = this.vardaVakajarjestajaService.getVakajarjestajat();
      try {
        this.vakajarjestajat.sort((a, b) => a.nimi.localeCompare(b.nimi, 'fi'));
      } catch (e) {
        console.log('Error on vakajarjestajat sorting', e);
      }
    });


    this.authService.getToimipaikkaAccessToAnyToimipaikka().subscribe(toimipaikkaAccessIfAny => {
      this.toimipaikkaAccessIfAnyToimipaikka = toimipaikkaAccessIfAny;
      if (this.vardaVakajarjestajaService.selectedVakajarjestaja) {
        this.tilapainenHenkilostoOnlyBoolean = this.authService.isTilapainenHenkilostoOnly();
      }
    });
  }

  changeVakajarjestaja(selectedVakajarjestaja: VardaVakajarjestajaUi): void {
    this.vardaVakajarjestajaService.setSelectedVakajarjestaja(selectedVakajarjestaja, true);
  }


  isAuthenticated(): boolean {
    return this.loginService.validApiToken;
  }

  ngOnInit() {
    const virkailijaRaamitUrl = this.vardaUtilityService.getVirkailijaRaamitUrl(window.location.hostname);
    if (virkailijaRaamitUrl) {
      this.virkailijaRaamit = true;
      const node = document.createElement('script');
      node.src = virkailijaRaamitUrl;
      node.type = 'text/javascript';
      node.async = true;
      document.getElementsByTagName('head')[0].appendChild(node);

      if (!window.location.hostname.includes('opintopolku.fi')) {
        setTimeout(() => window.document.dispatchEvent(new Event('DOMContentLoaded')), 500);
      }
    }
  }

}
