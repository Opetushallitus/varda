import { Component, OnInit } from '@angular/core';
import { Title} from '@angular/platform-browser';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { AuthService } from '../../../core/auth/auth.service';
import { TranslateService } from '@ngx-translate/core';
import { forkJoin, Observable, Subscription, throwError } from 'rxjs';
import { mergeMap, switchMap } from 'rxjs/operators';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { NgcCookieConsentService } from 'ngx-cookieconsent';
import { VardaToimipaikkaDTO, VardaVakajarjestajaUi } from '../../../utilities/models';
import { LoginService, VardaUserDTO, VardaKoodistoService } from 'varda-shared';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { environment } from '../../../../environments/environment';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-varda-dashboard',
  templateUrl: './varda-dashboard.component.html',
  styleUrls: ['./varda-dashboard.component.css']
})
export class VardaDashboardComponent implements OnInit {
  i18n = VirkailijaTranslations;
  ui: {
    isLoading: boolean,
    dashboardInitializationError: boolean,
    alertMsg: VirkailijaTranslations
  };

  private popupOpenSubscription: Subscription;

  constructor(
    private translateService: TranslateService,
    private vardaApiService: VardaApiService,
    private authService: AuthService,
    private loginService: LoginService,
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private ccService: NgcCookieConsentService,
  ) {
    this.ui = {
      isLoading: false,
      dashboardInitializationError: false,
      alertMsg: this.i18n.error_occured
    };

    this.vardaVakajarjestajaService.getSelectedVakajarjestajaObs().subscribe((data) => {
      if (data.onVakajarjestajaChange) {
        this.ui.isLoading = true;
        this.getToimipaikat().subscribe(this.onGetToimipaikatSuccess.bind(this), this.onGetToimipaikatError.bind(this));
      }
    });
  }

  getToimipaikat(): any {
    return this.vardaApiWrapperService
      .getAllToimipaikatForVakajarjestaja(this.vardaVakajarjestajaService.selectedVakajarjestaja.id);
  }

  onGetToimipaikatSuccess(toimipaikat_: Array<VardaToimipaikkaMinimalDto>): void {
    this.vardaVakajarjestajaService.setToimipaikat(toimipaikat_, this.authService);
    this.ui.isLoading = false;
  }

  onGetToimipaikatError(e: any): void {
    if (e?.noPrivileges) {
      this.ui.alertMsg = this.i18n.dashboard_error_contact_organisation_admin;
      this.ui.dashboardInitializationError = true;
    } else if (e?.isPalvelukayttaja) {
      this.ui.alertMsg = this.i18n.dashboard_error_palvelukayttaja_forbidden;
      this.ui.dashboardInitializationError = true;
    } else {
      this.onGetToimipaikatSuccess([]);
    }
    this.ui.isLoading = false;
  }

  setSelectedVakajarjestaja(vakajarjestajat: Array<VardaVakajarjestajaUi>): void {
    let selectedVakajarjestaja = vakajarjestajat[0];
    const vakajarjestajaFoundInLocalStorage = localStorage.getItem('varda.selectedvakajarjestaja');
    if (vakajarjestajaFoundInLocalStorage) {
      const parsedVakajarjestaja = JSON.parse(vakajarjestajaFoundInLocalStorage);
      selectedVakajarjestaja = vakajarjestajat.find(vakajarjestaja => vakajarjestaja.id === parsedVakajarjestaja.id);
      if (!selectedVakajarjestaja) {
        selectedVakajarjestaja = vakajarjestajat[0];
      }
    }

    this.vardaVakajarjestajaService.setSelectedVakajarjestaja(selectedVakajarjestaja);
  }

  setUserData(userData: VardaUserDTO): Observable<any> {
    return new Observable((setUserDataObserver) => {
      this.loginService.setUsername(userData.username);
      this.loginService.setUserEmail(userData.email);
      this.authService.setUserAsiointikieli(userData.asiointikieli_koodi);
      this.authService.setUserKayttooikeudet({
        kayttooikeudet: userData.kayttooikeudet,
        kayttajatyyppi: userData.kayttajatyyppi
      }).subscribe(() => {
        setUserDataObserver.next();
        setUserDataObserver.complete();
      }, (e) => setUserDataObserver.error(e));
    });
  }

  ngOnInit() {
    this.ui.isLoading = true;
    forkJoin([
      this.vardaApiWrapperService.getVakajarjestajaForLoggedInUser(),
    ]).pipe(mergeMap((data) => {
      const privileges = data[0];
      if (!privileges.length) {
        return throwError({ noPrivileges: true });
      }
      this.vardaVakajarjestajaService.setVakajarjestajat(privileges);
      this.setSelectedVakajarjestaja(privileges);
      return this.vardaApiService.getUserData();
    })).pipe(mergeMap((userData) => {
      return this.setUserData(userData);
    })).pipe(mergeMap(() => {
      return this.getToimipaikat();
    })).subscribe({
      next: this.onGetToimipaikatSuccess.bind(this),
      error: this.onGetToimipaikatError.bind(this)
    },
    );

    this.translateService.get([this.i18n.cookie_popup_message]).subscribe((translations) => {
      this.handleCookies(translations);
    });

    this.translateService.onLangChange.pipe(
      switchMap(() => this.translateService.get([this.i18n.cookie_popup_message]))
    ).subscribe((translations) => {
      this.handleCookies(translations);
    });

    this.popupOpenSubscription = this.ccService.popupOpen$.subscribe(() => { });
  }

  private handleCookies(translations) {
    this.ccService.getConfig().content = this.ccService.getConfig().content || {};
    // Override default messages with the translated ones
    this.ccService.getConfig().content.message = translations[this.i18n.cookie_popup_message];
    this.ccService.destroy();
    this.ccService.init(this.ccService.getConfig()); // update config with translated messages
  }
}
