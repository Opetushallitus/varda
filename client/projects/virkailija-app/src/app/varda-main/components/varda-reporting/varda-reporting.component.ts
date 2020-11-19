import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { Subscription } from 'rxjs';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { UserAccess, UserAccessKeys } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { filter } from 'rxjs/operators';
import { NavigationEnd, Router } from '@angular/router';

@Component({
  selector: 'app-varda-reporting',
  templateUrl: './varda-reporting.component.html',
  styleUrls: ['./varda-reporting.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class VardaReportingComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  userAccess: UserAccess;
  tilapainenHenkilostoOnly: boolean;
  subscriptions: Array<Subscription> = [];
  activeRoute: string;

  constructor(
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private authService: AuthService,
    private router: Router
  ) { }

  ngOnInit() {
    this.activeRoute = this.router.url.split('/').pop();
    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(event => {
        this.activeRoute = (<NavigationEnd>event).url.split('/').pop();
      })
    );

    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();

    this.subscriptions.push(
      this.authService.getToimipaikkaAccessToAnyToimipaikka().subscribe({
        next: accessIfAny => this.userAccess = accessIfAny,
        error: err => console.error(err)
      })
    );

    this.tilapainenHenkilostoOnly = this.authService.hasAccessOnlyTo([UserAccessKeys.tilapainenHenkilosto], true);
  }

  getVakajarjestajaId() {
    return this.selectedVakajarjestaja.id;
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
