import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { TranslateService } from '@ngx-translate/core';
import { take } from 'rxjs/operators';
import { interval } from 'rxjs';
import { HuoltajaTranslations } from '../../assets/i18n/translations.enum';
import { environment } from '../../environments/environment';
import { HuoltajaApiService } from './huoltaja-api.service';

@Injectable({
  providedIn: 'root'
})
export class OppijaRaamitService {
  translation = HuoltajaTranslations;

  constructor(private translateService: TranslateService, private huoltajaApiService: HuoltajaApiService) { }

  initRaamit(kutsumanimi?: string) {
    const vardaDomains = this.huoltajaApiService.getVardaDomains();
    if (!vardaDomains.some(hostname => window.location.hostname.endsWith(hostname))) {
      return false;
    }

    if (environment.production) {
      this.initMatomo();
    }

    const oppijaRaamit = `//${window.location.hostname}/oppija-raamit/js/apply-raamit.js`;
    const node = document.createElement('script');
    node.id = 'apply-raamit';
    node.src = oppijaRaamit;
    node.type = 'text/javascript';
    node.async = true;
    document.getElementsByTagName('head')[0].appendChild(node);

    if (!kutsumanimi) { // logout after 90s for unknown user
      this.logoutInterval(90);
    } else {
      this.logoutInterval(1800); // logout from oppija after 30 minutes
    }

    globalThis.Service = {
      getUser: () => {
        return new Promise((resolve) => resolve({ name: kutsumanimi || this.translateService.instant(this.translation.logout) }));
      },

      login: () => console.error('login to huoltaja-app should never happen through oppija-raamit'),

      logout: () => window.location.href = `${window.location.origin}/cas-oppija/logout`,

      changeLanguage: function (language: string) {
        return new Promise(resolve => {
          const lang = language === 'sv' ? 'sv' : 'fi';
          resolve(lang);
        });
      }
    };

  }

  private logoutInterval(seconds: number) {
    const logoutWarning = 60;
    const sekuntiInterval = interval(1000).pipe(take(seconds));

    sekuntiInterval.subscribe({
      next: counter => {
        const timeRemaining = seconds - counter;
        if (timeRemaining < logoutWarning) {
          const loginName = document.getElementsByClassName('header-logged-in-name')[0];
          loginName.innerHTML = `${this.translateService.instant(this.translation.poistu_palvelusta)} (${timeRemaining}s)`;
        }
      },
      complete: () => window.location.href = `${window.location.origin}/cas-oppija/logout`,
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
    /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
    _paq.push(['trackPageView']);
    _paq.push(['enableLinkTracking']);
    (function() {
      var u="//analytiikka.opintopolku.fi/matomo/";
      _paq.push(['setTrackerUrl', u+'matomo.php']);
      _paq.push(['setSiteId', '${siteID}']);
      var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
      g.type='text/javascript'; g.async=true; g.defer=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
    })();
    `;
    document.getElementsByTagName('head')[0].appendChild(node);
  }
}
