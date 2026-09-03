import { Component, OnDestroy } from '@angular/core';
import { switchMap } from 'rxjs/operators';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { Observable, of, Subscription } from 'rxjs';
import { Router } from '@angular/router';
import { AuthGuard } from '../../../core/auth/auth.guard';

@Component({
    selector: 'app-varda-dashboard',
    templateUrl: './varda-dashboard.component.html',
    styleUrls: ['./varda-dashboard.component.css'],
    standalone: false
})
export class VardaDashboardComponent implements OnDestroy {
  i18n = VirkailijaTranslations;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  subscriptions: Array<Subscription> = [];
  showUi = false;

  constructor(
    private authGuard: AuthGuard,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private router: Router
  ) {
    this.initListeners();
  }

  initListeners() {
    this.subscriptions.push(
      this.vardaVakajarjestajaService.listenSelectedVakajarjestaja().pipe(
        switchMap(vakajarjestaja => {
          // Hide UI to force component reload
          this.showUi = false;
          const previousVakajarjestaja = this.selectedVakajarjestaja;
          this.selectedVakajarjestaja = vakajarjestaja;

          if (!previousVakajarjestaja || previousVakajarjestaja === this.selectedVakajarjestaja) {
            // first init or vakajarjestaja is the same as previously, do not run login completion again
            return of(null);
          } else {
            // Organisaatio was changed, run login completion and return it as observable
            return new Observable(observer => {
              this.authGuard.completeLogin(observer, true);
            });
          }
        })
      ).subscribe( {
        next: () => {
          this.showUi = true;
          this.router.navigate(['/']);
        },
        error: () => this.showUi = true
      })
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }
}
