import {AfterViewInit, Component, Inject, DOCUMENT} from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaDomService } from './core/services/varda-dom.service';

import { Title } from '@angular/platform-browser';
import { Router, NavigationEnd } from '@angular/router';
import { LoadingHttpService, LoginService, HelperService, VardaKoodistoService, VardaUserDTO } from 'varda-shared';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';
import { environment } from '../environments/environment';
import { VardaCookieEnum } from './utilities/models/enums/varda-cookie.enum';
import { VardaApiService } from './core/services/varda-api.service';
import { VirkailijaTranslations } from '../assets/i18n/virkailija-translations.enum';

declare const matomoPageChange: any;

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css'],
    standalone: false
})
export class AppComponent implements AfterViewInit {
  isLoading: Observable<boolean>;
  i18n = VirkailijaTranslations;

  constructor(
    private titleService: Title,
    private router: Router,
    private apiService: VardaApiService,
    private translateService: TranslateService,
    private koodistoService: VardaKoodistoService,
    private vardaDomService: VardaDomService,
    private loadingHttpService: LoadingHttpService,
    private loginService: LoginService,
    private helperService: HelperService,
    @Inject(DOCUMENT) private _document: any) {

    this.initKoodistotAndLanguage();
    this.loginService.initBroadcastChannel(VardaCookieEnum.api_token);

    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.setTitle(router);
      }
    });

    this.isLoading = this.loadingHttpService.isLoadingWithDebounce();

    this.helperService.setTranslateService(this.translateService);
  }

  ngAfterViewInit() {
    const jumpElement = document.getElementById('jump-link');
    document.body.insertBefore(jumpElement, document.body.firstChild);

    const mutationObserver = new MutationObserver(mutationList => {
      mutationList.forEach(mutation => {
        mutation.addedNodes.forEach(addedNode => {
          if (addedNode.nodeType === Node.ELEMENT_NODE && (addedNode as Element).id === 'raamit_app_root') {
            // Virkailija-raamit have now been added, we can move jump link to the beginning
            document.body.insertBefore(jumpElement, document.body.firstChild);
          }
        });
      });
    });
    // Observe body and its children
    mutationObserver.observe(document.body, {childList: true});
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

  initKoodistotAndLanguage() {
    const defaultLanguage = this.translateService.getBrowserLang() === 'sv' ? 'sv' : 'fi';
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this.vardaDomService.bindTabAndClickEvents();

    this.loginService.getCurrentUser().pipe(filter(Boolean)).subscribe((user: VardaUserDTO) => {
      const userLanguage = user.toimintakieli_koodi.toLocaleLowerCase() === 'sv' ? 'sv' : 'fi';
      this._document.documentElement.lang = userLanguage;
      this.translateService.use(userLanguage);
      this.setTitle(this.router);
      this.koodistoService.initKoodistot(environment.vardaAppUrl, userLanguage);
      this.loginService.initLogoutInterval(90 * 60, this.translateService, this.apiService.getLogoutCasUrl());
    });
  }

  onJumpClick(event: Event) {
    event.preventDefault();
    document.getElementById('main-content').focus({preventScroll: true});
  }
}
