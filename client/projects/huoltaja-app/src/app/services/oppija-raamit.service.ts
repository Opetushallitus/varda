import { Injectable } from '@angular/core';
import { filter } from 'rxjs/operators';
import { BehaviorSubject } from 'rxjs';
import { HuoltajaTranslations } from '../../assets/i18n/translations.enum';
import { environment } from '../../environments/environment';
import { HuoltajaApiService } from './huoltaja-api.service';
import { TranslateService } from '@ngx-translate/core';
import { MatomoService } from 'varda-shared';

@Injectable({
  providedIn: 'root'
})
export class OppijaRaamitService {
  translation = HuoltajaTranslations;
  private redirectURL = encodeURI(`${window.location.origin}/oma-opintopolku/`);
  private logoutURL = `${window.location.origin}/cas-oppija/logout?service=${this.redirectURL}`;
  private username$ = new BehaviorSubject<string>(null);

  constructor(
    private huoltajaApiService: HuoltajaApiService,
    private translate: TranslateService,
    private matomo: MatomoService
  ) { }

  initRaamit() {
    const vardaDomains = this.huoltajaApiService.getVardaDomains();
    if (!vardaDomains.some(hostname => window.location.hostname.endsWith(hostname))) {
      return false;
    }

    if (environment.production) {
      const [productionID, qaID] = [25, 26];
      this.matomo.initMatomo(vardaDomains.includes(window.location.hostname) ? productionID : qaID);
    }

    this.raamitScript();
    this.cookieScript();
  }

  setUsername(username: string) {
    this.username$.next(username);
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

  getLogoutURL() {
    return this.logoutURL;
  }
}
