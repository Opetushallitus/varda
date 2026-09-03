import { Component, Inject, OnDestroy, OnInit, DOCUMENT } from '@angular/core';
import { LangChangeEvent, TranslateService } from '@ngx-translate/core';

import { Observable, Subscription } from 'rxjs';
import { delay } from 'rxjs/operators';
import { LoadingHttpService, VardaKoodistoService, SupportedLanguage, HelperService } from 'varda-shared';
import { NavigationEnd, Router } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { PublicTranslations } from '../assets/i18n/translations.enum';
import { environment } from '../environments/environment';

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css'],
    standalone: false
})
export class AppComponent implements OnInit, OnDestroy {
  translation = PublicTranslations;
  isLoading: Observable<boolean>;
  private pageTitleTranslations: Array<string>;
  private pageTitleStatic: Array<string>;
  private translationSubscription: Subscription;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private translateService: TranslateService,
    private helperService: HelperService,
    private koodistoService: VardaKoodistoService,
    private loadingHttpService: LoadingHttpService,
    private router: Router,
    private titleService: Title,
    @Inject(DOCUMENT) private document: Document
  ) {
    this.helperService.setTranslateService(this.translateService);
  }

  ngOnInit(): void {
    const defaultLanguage = this.translateService.getBrowserLang() === 'sv' ? 'sv' : 'fi';
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this.document.documentElement.lang = defaultLanguage;

    this.koodistoService.initKoodistot(environment.backendUrl, defaultLanguage);

    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));

    this.subscriptions.push(
      this.router.events.subscribe(event => {
        if (event instanceof NavigationEnd) {
          this.parseTitle();
        }
      }),
      this.translateService.onLangChange.subscribe((params: LangChangeEvent) => {
        const newLang = ['fi', 'sv'].includes(params.lang.toLowerCase()) ? params.lang.toLowerCase() : 'fi';
        this.koodistoService.initKoodistot(environment.backendUrl, newLang as SupportedLanguage);
      })
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  private parseTitle() {
    this.pageTitleTranslations = [];
    this.pageTitleStatic = [];

    this.pageTitleTranslations.push(this.translation.varda_title);

    let snapshot = this.router.routerState.root.snapshot.firstChild;
    while (snapshot) {
      // Get page title from router data
      if (snapshot.data.title) {
        this.pageTitleTranslations.push(snapshot.data.title);
      }
      // Get koodisto name from params
      if (snapshot.params.koodisto) {
        this.pageTitleStatic.push(snapshot.params.koodisto);
      }

      snapshot = snapshot.firstChild;
    }

    this.setTitle();
  }

  private setTitle() {
    if (this.translationSubscription) {
      this.translationSubscription.unsubscribe();
    }
    this.translationSubscription = this.translateService.stream(this.pageTitleTranslations).subscribe(data => {
      const reversedTitle = Object.values(data).reverse() as (Array<string>);
      const titleArray = this.pageTitleStatic.concat(reversedTitle);
      this.titleService.setTitle(titleArray.join(' - '));
    });
  }
}
