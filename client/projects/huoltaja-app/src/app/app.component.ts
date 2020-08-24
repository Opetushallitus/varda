import { Component, OnInit, Inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';
import { LoadingHttpService } from 'varda-shared';
import { Observable } from 'rxjs/internal/Observable';
import { delay } from 'rxjs/internal/operators/delay';
import { DOCUMENT } from '@angular/common';
import { HuoltajaApiService } from './services/huoltaja-api.service';
import { CookieService } from 'ngx-cookie-service';
import { HuoltajaTranslations } from '../assets/i18n/translations.enum';
import { OppijaRaamitService } from './services/oppija-raamit.service';
import { filter } from 'rxjs/internal/operators/filter';
import { HuoltajanLapsiDTO } from './utilities/models/dto/huoltajan-lapsi-dto';

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
    private huoltajaApi: HuoltajaApiService,
    private translateService: TranslateService,
    private titleService: Title,
    private loadingHttpService: LoadingHttpService,
    @Inject(DOCUMENT) private _document: any
  ) {
    this.initLanguage();
    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));

    this.huoltajaApi.getCurrentUser().pipe(filter(Boolean)).subscribe((user: HuoltajanLapsiDTO) => {
      this.oppijaRaamit.initRaamit(user.henkilo?.kutsumanimi);
    }, () => {
      this.oppijaRaamit.initRaamit();
    });
  }

  ngOnInit() {
    this.translateService.get(this.translation.page_title).subscribe(name => {
      this.titleService.setTitle(name);
    });
  }

  initLanguage() {
    const getLanguage = () => {
      const languageCookie = this.cookieService.get('lang')?.toLocaleLowerCase();
      const language = languageCookie || this.translateService.getBrowserLang();
      return language === 'sv' ? 'sv' : 'fi';
    };

    const defaultLanguage = getLanguage();
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this._document.documentElement.lang = defaultLanguage;
  }

}


