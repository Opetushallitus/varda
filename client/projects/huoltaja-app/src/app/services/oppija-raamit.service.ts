import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { TranslateService } from '@ngx-translate/core';
import { take } from 'rxjs/operators';
import { interval } from 'rxjs';
import { Translations } from '../../assets/i18n/translations.enum';

@Injectable({
  providedIn: 'root'
})
export class OppijaRaamitService {
  translation = Translations;

  constructor(private http: LoadingHttpService,
    private translateService: TranslateService) { }

  initRaamit(kutsumanimi?: string) {
    const oppijaRaamit = window.location.hostname.endsWith('opintopolku.fi') ? `//${window.location.hostname}/oppija-raamit/js/apply-raamit.js` : null;
    if (!oppijaRaamit) {
      return false;
    }

    const node = document.createElement('script');
    node.id = 'apply-raamit';
    node.src = oppijaRaamit;
    node.type = 'text/javascript';
    node.async = true;
    document.getElementsByTagName('head')[0].appendChild(node);

    if (!kutsumanimi) { // logout after 60s for unknown user
      this.logoutInterval(60);
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
          loginName.innerHTML = `${this.translateService.instant(this.translation.poistu)} (${timeRemaining}s)`;
        }
      },
      complete: () => window.location.href = `${window.location.origin}/cas-oppija/logout`,
    });
  }
}
