import { Injectable } from '@angular/core';
import { filter, take } from 'rxjs/operators';
import { BehaviorSubject, interval } from 'rxjs';
import { HuoltajaTranslations } from '../../assets/i18n/translations.enum';
import { environment } from '../../environments/environment';
import { HuoltajaApiService } from './huoltaja-api.service';
import { MatSnackBar, MatSnackBarRef } from '@angular/material/snack-bar';
import { HuoltajaTimeoutComponent } from '../huoltaja-main/components/utility-components/huoltaja-timeout/huoltaja-timeout.component';
import { TranslateService } from '@ngx-translate/core';

@Injectable({
  providedIn: 'root'
})
export class OppijaRaamitService {
  translation = HuoltajaTranslations;
  private lastHttpRequest = Date.now();
  private redirectURL = encodeURI(`${window.location.origin}/oma-opintopolku/`);
  private logoutURL = `${window.location.origin}/cas-oppija/logout?service=${this.redirectURL}`;
  private username$ = new BehaviorSubject<string>(null);
  private snackbarVisible = false;

  constructor(
    private huoltajaApiService: HuoltajaApiService,
    private snackbar: MatSnackBar,
    private translate: TranslateService
  ) { }

  initRaamit() {
    const vardaDomains = this.huoltajaApiService.getVardaDomains();
    if (!vardaDomains.some(hostname => window.location.hostname.endsWith(hostname))) {
      return false;
    }

    if (environment.production) {
      this.initMatomo();
    }

    this.raamitScript();
    this.cookieScript();
  }

  private logoutInterval(seconds: number) {
    const logoutWarning = 180;
    const secondInterval = interval(1000);
    let snackBarRef: MatSnackBarRef<any> = null;
    let lastCheckAt = 0;

    secondInterval.subscribe({
      next: counter => {
        const now = Date.now() / 1000;
        const logoutAt = this.lastHttpRequest / 1000 + seconds;
        const timeRemaining = Math.floor(logoutAt - now);

        if (lastCheckAt !== this.lastHttpRequest) {
          snackBarRef?.dismiss();
          lastCheckAt = this.lastHttpRequest;
        }

        if (timeRemaining < logoutWarning) {
          if (!this.snackbarVisible) {
            snackBarRef = this.snackbar.openFromComponent(HuoltajaTimeoutComponent, {
              data: {
                seconds: timeRemaining,
                dismiss: () => snackBarRef.dismiss()
              }
            });
            snackBarRef.afterOpened().pipe(take(1)).subscribe(() => this.snackbarVisible = true);
            snackBarRef.afterDismissed().pipe(take(1)).subscribe(() => {
              this.snackbarVisible = false;
              this.clearLogoutInterval();
            });
          }

          if (timeRemaining < 0 && window.location.hostname !== 'localhost') {
            window.location.href = this.logoutURL;
          }
        }
      }
    });
  }

  initMatomo() {
    let siteID = 26;
    if (window.location.hostname === 'opintopolku.fi' || window.location.hostname === 'studieinfo.fi' || window.location.hostname === 'studyinfo.fi') {
      siteID = 25;
    }
    const node = document.createElement('script');
    node.id = 'matomo';
    node.type = 'text/javascript';
    node.async = true;
    node.innerHTML = `
    var _paq = window._paq || [];

    function vardaPageChange(title, path) {
      _paq.push(['setCustomUrl', path]);
      _paq.push(['setDocumentTitle', title]);
      _paq.push(['trackPageView']);
      _paq.push(['enableLinkTracking']);
    }

    (function() {
      var u="//analytiikka.opintopolku.fi/matomo/";
      _paq.push(['setTrackerUrl', u+'matomo.php']);
      _paq.push(['setSiteId', '${siteID}']);
      var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
      g.type='text/javascript'; g.id='matomoX'; g.async=true; g.defer=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
    })();
    `;
    document.getElementsByTagName('head')[0].appendChild(node);
  }

  setUsername(username: string) {
    this.logoutInterval(1200);
    this.username$.next(username);
  }

  clearLogoutInterval() {
    if (!this.snackbarVisible) {
      this.lastHttpRequest = Date.now();
    }
  }

  raamitScript() {
    globalThis.Service = {
      getUser: () => {
        return new Promise((resolve) =>
          this.username$.pipe(filter(Boolean)).subscribe(username => resolve({ name: username }))
        );
      },

      login: () => console.error('login to huoltaja-app should never happen through oppija-raamit'),
      logout: () => window.location.href = this.logoutURL,

      changeLanguage: function (language: string) {
        return new Promise(resolve => {
          const lang = language === 'sv' ? 'sv' : 'fi';
          resolve(lang);
        });
      }
    };

    const node = document.createElement('script');
    node.id = 'apply-raamit';
    node.src = `//${window.location.hostname}/oppija-raamit/js/apply-raamit.js`;
    node.type = 'text/javascript';
    node.async = true;
    document.getElementsByTagName('head')[0].appendChild(node);
  }

  cookieScript() {
    const node = document.createElement('script');
    node.id = 'apply-modal';
    node.src = `//${window.location.hostname}/oppija-raamit/js/apply-modal.js`;
    node.type = 'text/javascript';
    node.async = true;
    node.lang = this.translate.getDefaultLang();
    node.setAttribute('sdg', 'false');
    document.getElementsByTagName('head')[0].appendChild(node);
  }
}
