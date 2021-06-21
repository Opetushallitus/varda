import { Component, OnDestroy } from '@angular/core';
import { AuthService } from '../../../core/auth/auth.service';
import { mergeMap } from 'rxjs/operators';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { of, Subscription } from 'rxjs';

@Component({
  selector: 'app-varda-dashboard',
  templateUrl: './varda-dashboard.component.html',
  styleUrls: ['./varda-dashboard.component.css']
})
export class VardaDashboardComponent implements OnDestroy {
  i18n = VirkailijaTranslations;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  toimipaikkaAccessToAnyToimipaikka: UserAccess;
  tilapainenHenkilostoOnly: boolean;
  subscriptions: Array<Subscription> = [];
  ui: {
    isLoading: boolean;
    dashboardInitializationError: boolean;
    alertMsg: VirkailijaTranslations;
  };

  constructor(
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
  ) {
    this.ui = {
      isLoading: null,
      dashboardInitializationError: false,
      alertMsg: this.i18n.error_occured
    };
    this.initListeners();
  }


  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }

  initListeners() {
    this.subscriptions.push(
      this.vardaVakajarjestajaService.listenSelectedVakajarjestaja().pipe(
        mergeMap(vakajarjestaja => {
          this.toimipaikkaAccessToAnyToimipaikka = null;
          const previousVakajarjestaja = this.selectedVakajarjestaja;
          this.selectedVakajarjestaja = vakajarjestaja;
          // first init or vakajarjestaja is the same as previously
          if (!previousVakajarjestaja || previousVakajarjestaja === vakajarjestaja) {
            return of(null);
          }
          return this.vakajarjestajaApiService.getToimipaikat(vakajarjestaja.id);
        })
      ).pipe(
        mergeMap(toimipaikat => {
          if (toimipaikat) {
            this.vardaVakajarjestajaService.setToimipaikat(toimipaikat);
          }
          return this.authService.getToimipaikkaAccessToAnyToimipaikka();
        })
      ).subscribe(toimipaikkaAccessToAnyToimipaikka =>
        this.toimipaikkaAccessToAnyToimipaikka = toimipaikkaAccessToAnyToimipaikka
      )
    );
  }

}
