import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { Subscription } from 'rxjs';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { filter } from 'rxjs/operators';
import { NavigationEnd, Router } from '@angular/router';

@Component({
    selector: 'app-varda-reporting',
    templateUrl: './varda-reporting.component.html',
    styleUrls: ['./varda-reporting.component.css'],
    encapsulation: ViewEncapsulation.None,
    standalone: false
})
export class VardaReportingComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  userAccess: UserAccess;
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
        this.activeRoute = (event as NavigationEnd).url.split('/').pop();
      })
    );

    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
    this.userAccess = this.authService.anyUserAccess;
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
