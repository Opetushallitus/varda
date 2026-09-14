import { Component, Inject, HostListener, AfterViewInit, DOCUMENT } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';
import { LoadingHttpService, LoginService, SupportedLanguage, HelperService, VardaUserDTO } from 'varda-shared';
import { Observable } from 'rxjs';
import { filter, take } from 'rxjs/operators';

import { CookieService } from 'ngx-cookie-service';
import { HuoltajaTranslations } from '../assets/i18n/translations.enum';
import { OppijaRaamitService } from './services/oppija-raamit.service';
import { HuoltajaCookieEnum } from './utilities/models/enum/huoltaja-cookie.enum';
import { NavigationEnd, Router } from '@angular/router';

declare const matomoPageChange: any;

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css'],
    standalone: false
})
export class AppComponent implements AfterViewInit {
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
    private helperService: HelperService,
    @Inject(DOCUMENT) private _document: any
  ) {
    this.initLanguage();
    this.loginService.initBroadcastChannel('huoltaja.api.token');
    this.isLoading = this.loadingHttpService.isLoadingWithDebounce();

    this.helperService.setTranslateService(this.translateService);

    this.oppijaRaamit.initRaamit();

    this.loginService.getCurrentUser().pipe(filter(Boolean), take(1)).subscribe((henkilotiedot: VardaUserDTO) => {
      const displayName =
        [henkilotiedot?.kutsumanimi, henkilotiedot?.sukunimi]
          .filter(Boolean)
          .join(' ') || henkilotiedot?.username;
      this.oppijaRaamit.setUsername(displayName);
      this.loginService.initLogoutInterval(20 * 60, this.translateService, this.oppijaRaamit.getLogoutURL());
    });

    this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(() => {
      this.setTitle(router);
    });
  }

  ngAfterViewInit() {
    const jumpElement = document.getElementById('jump-link');
    document.body.insertBefore(jumpElement, document.body.firstChild);

    const mutationObserver = new MutationObserver(mutationList => {
      mutationList.forEach(mutation => {
        mutation.addedNodes.forEach(addedNode => {
          if (addedNode.nodeType === Node.ELEMENT_NODE &&
            (addedNode as Element).hasAttribute('data-raamit-component')) {
            // Oppija-raamit have now been added, we can move jump link to the beginning
            document.body.insertBefore(jumpElement, document.body.firstChild);
          }
        });
      });
    });
    // Observe body and its children
    mutationObserver.observe(document.body, {childList: true});
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering
  @HostListener('document:keydown', ['$event'])
  @HostListener('document:click', ['$event'])
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  documentClick(event: MouseEvent) {
    this.loginService.clearLogoutInterval();
  }

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

  setTitle(router: Router): void {
    const titles: Array<string> = [...this.getTitle(router.routerState, router.routerState.root).reverse(), 'Varda'];
    this.translateService.get(titles).subscribe(
      translation => {
        const nextTitle = titles.map(title => translation[title]).join(' - ');
        this.titleService.setTitle(nextTitle);
        try {
          matomoPageChange(nextTitle, window.location.pathname);
        } catch (e) {
          console.log(e);
        }
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

  onJumpClick(event: Event) {
    event.preventDefault();
    document.getElementById('main-content').focus({preventScroll: true});
  }
}
