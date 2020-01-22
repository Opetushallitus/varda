import {Component, OnInit} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {VardaApiService} from '../../../core/services/varda-api.service';
import {AuthService} from '../../../core/auth/auth.service';
import {TranslateService} from '@ngx-translate/core';
import {forkJoin, Observable, Subscription, throwError} from 'rxjs';
import {mergeMap, switchMap} from 'rxjs/operators';
import {VardaKielikoodistoService} from '../../../core/services/varda-kielikoodisto.service';
import {VardaKuntakoodistoService} from '../../../core/services/varda-kuntakoodisto.service';
import {VardaApiWrapperService} from '../../../core/services/varda-api-wrapper.service';
import {VardaVakajarjestajaService} from '../../../core/services/varda-vakajarjestaja.service';
import {NgcCookieConsentService} from 'ngx-cookieconsent';
import {VardaToimipaikkaDTO} from '../../../utilities/models';
import {Router} from '@angular/router';
import {VardaMaksunPerusteKoodistoService} from '../../../core/services/varda-maksun-peruste-koodisto.service';
import {LoginService, VardaUserDTO} from 'varda-shared';
import {VardaToimipaikkaMinimalDto} from '../../../utilities/models/dto/varda-toimipaikka-dto.model';

@Component({
  selector: 'app-varda-dashboard',
  templateUrl: './varda-dashboard.component.html',
  styleUrls: ['./varda-dashboard.component.css']
})
export class VardaDashboardComponent implements OnInit {

  ui: {
    isLoading: boolean,
    dashboardInitializationError: boolean,
    alertMsg: string
  };

  private popupOpenSubscription: Subscription;
  toimipaikat: Array<VardaToimipaikkaDTO>;

  constructor(
    private translateService: TranslateService,
    private titleService: Title,
    private vardaApiService: VardaApiService,
    private authService: AuthService,
    private loginService: LoginService,
    private vardaKielikoodistoService: VardaKielikoodistoService,
    private vardaKuntakoodistoService: VardaKuntakoodistoService,
    private vardaMaksunPerusteKoodistoService: VardaMaksunPerusteKoodistoService,
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private ccService: NgcCookieConsentService,
    private router: Router) {
      this.ui = {
        isLoading: false,
        dashboardInitializationError: false,
        alertMsg: 'alert.error-occurred'
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
    this.toimipaikat = this.vardaVakajarjestajaService.getTallentajaToimipaikat();
    setTimeout(() => {
      this.authService.initKayttooikeudet();
    });
    this.ui.isLoading = false;
  }

  onGetToimipaikatError(e: any): any {
    console.log(e);
    if (e.noPrivileges) {
      this.ui.alertMsg = 'alert.contact-organisation-admin-user';
    } else if (e.isPalvelukayttaja) {
      this.ui.alertMsg = 'alert.palvelukayttaja-forbidden';
    }

    this.ui.dashboardInitializationError = true;
    this.ui.isLoading = false;
  }

  setSelectedVakajarjestaja(vakajarjestajat: any): void {
    let selectedVakajarjestaja = vakajarjestajat[0];
    const vakajarjestajaFoundInLocalStorage = localStorage.getItem('varda.selectedvakajarjestaja');
    if (vakajarjestajaFoundInLocalStorage) {
        const parsedVakajarjestaja = JSON.parse(vakajarjestajaFoundInLocalStorage);
        selectedVakajarjestaja = this.vardaVakajarjestajaService.getVakajarjestajaByUrl(parsedVakajarjestaja.url, vakajarjestajat);
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
      this.authService.setUserKayttooikeudet({kayttooikeudet: userData.kayttooikeudet,
        kayttajatyyppi: userData.kayttajatyyppi}).subscribe(() => {
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
        return throwError({noPrivileges: true});
      }
      this.vardaVakajarjestajaService.setVakajarjestajat(privileges);
      this.setSelectedVakajarjestaja(privileges);
      return this.vardaApiService.getUserData();
    })).pipe(mergeMap((userData) => {
      return this.setUserData(userData);
    })).pipe(mergeMap(() => {
      return forkJoin([
        this.vardaKuntakoodistoService.initKuntakoodisto(),
        this.vardaKielikoodistoService.initKielikoodisto(),
        this.vardaMaksunPerusteKoodistoService.initialise(),
      ]);
    })).pipe(mergeMap(() => {
      return this.getToimipaikat();
    })).subscribe({
        next: this.onGetToimipaikatSuccess.bind(this),
        error: this.onGetToimipaikatError.bind(this)},
    );

    this.translateService.get(['label.varda-dashboard', 'cookie.message']).subscribe((translations) => {
      this.handleCookies(translations);
    });

    this.translateService.onLangChange.pipe(
      switchMap(() => this.translateService.get(['label.varda-dashboard', 'cookie.message']))
    ).subscribe((translations) => {
      this.handleCookies(translations);
    });

    this.popupOpenSubscription = this.ccService.popupOpen$.subscribe(() => {});
  }

  private handleCookies(translations) {
    this.titleService.setTitle(translations['label.varda-dashboard']);
    this.ccService.getConfig().content = this.ccService.getConfig().content || {} ;
    // Override default messages with the translated ones
    this.ccService.getConfig().content.message = translations['cookie.message'];
    this.ccService.destroy();
    this.ccService.init(this.ccService.getConfig()); // update config with translated messages
  }
}
