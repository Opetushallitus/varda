import { Component, OnInit, Inject, HostListener } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';
import { LoadingHttpService, LoginService, VardaUserDTO } from 'varda-shared';
import { Observable } from 'rxjs';
import { filter, take } from 'rxjs/operators';
import { DOCUMENT } from '@angular/common';
import { CookieService } from 'ngx-cookie-service';
import { HuoltajaTranslations } from '../assets/i18n/translations.enum';
import { OppijaRaamitService } from './services/oppija-raamit.service';
import { HuoltajaCookieEnum } from './utilities/models/enum/huoltaja-cookie.enum';

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
    private loadingHttpService: LoadingHttpService,
    @Inject(DOCUMENT) private _document: any
  ) {
    this.initLanguage();
    this.loginService.initBroadcastChannel('huoltaja.api.token');
    this.isLoading = this.loadingHttpService.isLoadingWithDebounce();

    this.oppijaRaamit.initRaamit();

    this.loginService.getCurrentUser().pipe(filter(Boolean), take(1)).subscribe((henkilotiedot: VardaUserDTO) =>
      this.oppijaRaamit.setUsername(henkilotiedot?.kutsumanimi || henkilotiedot.username)
    );
  }

  ngOnInit() {
    this.translateService.get(this.translation.page_title).subscribe(name => {
      this.titleService.setTitle(name);
    });
  }

  initLanguage() {
    const getLanguage = () => {
      const languageCookie = this.cookieService.get(HuoltajaCookieEnum.lang);
      const language = languageCookie || this.translateService.getBrowserLang();
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
    this.oppijaRaamit.clearLogoutInterval();
  }
}


