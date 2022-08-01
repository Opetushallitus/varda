import { Component, OnDestroy } from '@angular/core';
import { AuthService } from '../../../core/auth/auth.service';
import { mergeMap } from 'rxjs/operators';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { of, Subscription } from 'rxjs';
import { Router } from '@angular/router';

@Component({
  selector: 'app-varda-dashboard',
  templateUrl: './varda-dashboard.component.html',
  styleUrls: ['./varda-dashboard.component.css']
})
export class VardaDashboardComponent implements OnDestroy {
  i18n = VirkailijaTranslations;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  subscriptions: Array<Subscription> = [];
  showUi = false;

  constructor(
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private router: Router
  ) {
    this.initListeners();
  }

  initListeners() {
    this.subscriptions.push(
      this.vardaVakajarjestajaService.listenSelectedVakajarjestaja().pipe(
        mergeMap(vakajarjestaja => {
          // Hide UI to force component reload
          this.showUi = false;
          const previousVakajarjestaja = this.selectedVakajarjestaja;
          this.selectedVakajarjestaja = vakajarjestaja;
          // first init or vakajarjestaja is the same as previously
          if (!previousVakajarjestaja || previousVakajarjestaja === vakajarjestaja) {
            return of(null);
          }
          return this.vakajarjestajaApiService.getToimipaikat(vakajarjestaja.id);
        })
      ).subscribe(toimipaikat => {
        if (toimipaikat) {
          // Organisaatio was changed
          this.vardaVakajarjestajaService.setToimipaikat(toimipaikat);
          this.authService.initUserPermissions();
          // Navigate to default location
          this.router.navigate(['/']);
        }
        this.showUi = true;
      })
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }
}
