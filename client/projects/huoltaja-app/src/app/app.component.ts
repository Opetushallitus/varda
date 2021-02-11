import { Component, OnInit, Inject, HostListener } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';
import { LoadingHttpService, LoginService, SupportedLanguage, VardaUserDTO } from 'varda-shared';
import { Observable } from 'rxjs';
import { filter, take } from 'rxjs/operators';
import { DOCUMENT } from '@angular/common';
import { CookieService } from 'ngx-cookie-service';
import { HuoltajaTranslations } from '../assets/i18n/translations.enum';
import { OppijaRaamitService } from './services/oppija-raamit.service';
import { HuoltajaCookieEnum } from './utilities/models/enum/huoltaja-cookie.enum';
import { NavigationEnd, Router } from '@angular/router';

declare const vardaPageChange: any;

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  isLoading: Observable<boolean>;
  translation = HuoltajaTranslations;

  constructor(
    private oppijaRaamit: OppijaRaamitService,
    private cookieService: CookieService,
    private loginService: LoginService,
    private translateService: TranslateService,
    private titleService: Title,
    private router: Router,
    private loadingHttpService: LoadingHttpService,
    @Inject(DOCUMENT) private _document: any
  ) {
    this.initLanguage();
    this.loginService.initBroadcastChannel('huoltaja.api.token');
    this.isLoading = this.loadingHttpService.isLoadingWithDebounce();

    this.oppijaRaamit.initRaamit();

    this.loginService.getCurrentUser().pipe(filter(Boolean), take(1)).subscribe((henkilotiedot: VardaUserDTO) => {
      this.oppijaRaamit.setUsername(henkilotiedot?.kutsumanimi || henkilotiedot.username);
      this.loginService.initLogoutInterval(20 * 60, this.translateService, this.oppijaRaamit.getLogoutURL());
    });

    this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(event => {
      this.setTitle(router);
    });
  }

  ngOnInit() { }

  initLanguage() {
    const getLanguage = () => {
      const languageCookie = this.cookieService.get(HuoltajaCookieEnum.lang);
      const language = (languageCookie || this.translateService.getBrowserLang()) as SupportedLanguage;
      return language?.toLocaleLowerCase() === 'sv' ? 'sv' : 'fi';
    };

    const defaultLanguage = getLanguage();
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this._document.documentElement.lang = defaultLanguage;
  }

  @HostListener('document:keydown', ['$event'])
  @HostListener('document:click', ['$event'])
  documentClick(event: MouseEvent) {
    this.loginService.clearLogoutInterval();
  }


  setTitle(router: Router): void {
    const titles: Array<string> = [...this.getTitle(router.routerState, router.routerState.root).reverse(), 'Varda'];
    this.translateService.get(titles).subscribe(
      translation => {
        const nextTitle = titles.map(title => translation[title]).join(' - ');
        this.titleService.setTitle(nextTitle);
        try {
          vardaPageChange(nextTitle, window.location.pathname);
        } catch (e) { }
      }
    );
  }

  getTitle(state: any, parent: any): string[] {
    const data = [];
    if (parent && parent.snapshot.data && parent.snapshot.data.title) {
      data.push(parent.snapshot.data.title);
    }

    if (state && parent) {
      data.push(...this.getTitle(state, state.firstChild(parent)));
    }

    return data;
  }
}


