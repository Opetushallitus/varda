import { Component, Input, OnDestroy } from '@angular/core';
import { NavigationEnd, Router, ActivatedRoute } from '@angular/router';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { UserAccess, UserAccessKeys } from '../../../utilities/models/varda-user-access.model';
import { filter } from 'rxjs/operators';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { AuthService } from '../../../core/auth/auth.service';
import { Subscription } from 'rxjs';


@Component({
  selector: 'app-varda-header',
  templateUrl: './varda-header.component.html',
  styleUrls: ['./varda-header.component.css']
})
export class VardaHeaderComponent implements OnDestroy {
  @Input() selectedVakajarjestaja: VardaVakajarjestajaUi;
  @Input() toimipaikkaAccessToAnyToimipaikka: UserAccess;
  tilapainenHenkilostoOnly: boolean;
  vakajarjestajat: Array<VardaVakajarjestajaUi>;
  i18n = VirkailijaTranslations;
  toimipaikkaSelected: boolean;
  activeNavItem: string;
  subscriptions: Array<Subscription> = [];



  constructor(
    private activatedRoute: ActivatedRoute,
    private router: Router,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private authService: AuthService
  ) {

    this.tilapainenHenkilostoOnly = this.authService.hasAccessOnlyTo([UserAccessKeys.tilapainenHenkilosto], true);

    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe((navigationEnd) => {
        let topRoute = this.activatedRoute.firstChild;
        while (topRoute?.firstChild) {
          topRoute = topRoute.firstChild;
        }

        this.activeNavItem = topRoute.snapshot?.data?.nav_item || topRoute.snapshot.routeConfig.path;
      })
    );


    this.vardaVakajarjestajaService.getVakajarjestajat().pipe(filter(Boolean)).subscribe((vakajarjestajat: Array<VardaVakajarjestajaUi>) => {
      this.vakajarjestajat = vakajarjestajat;
      this.vakajarjestajat.sort((a, b) => a.nimi?.localeCompare(b.nimi, 'fi'));
    });
  }

  changeVakajarjestaja(selectedVakajarjestaja: VardaVakajarjestajaUi): void {
    this.vardaVakajarjestajaService.setSelectedVakajarjestaja(selectedVakajarjestaja);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }
}
