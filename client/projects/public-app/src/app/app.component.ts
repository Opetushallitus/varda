import { Component, Inject, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { DOCUMENT } from '@angular/common';
import { Observable, Subscription } from 'rxjs';
import { delay } from 'rxjs/operators';
import { LoadingHttpService } from 'varda-shared';
import { NavigationEnd, Router } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { PublicTranslations } from '../assets/i18n/translations.enum';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  translation = PublicTranslations;
  isLoading: Observable<boolean>;
  private pageTitleTranslations: Array<string>;
  private pageTitleStatic: Array<string>;
  private translationSubscription: Subscription;

  constructor(private translateService: TranslateService,
    private loadingHttpService: LoadingHttpService,
    private router: Router,
    private titleService: Title,
    @Inject(DOCUMENT) private document: Document) { }

  ngOnInit(): void {
    const defaultLanguage = this.translateService.getBrowserLang() === 'sv' ? 'sv' : 'fi';
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this.document.documentElement.lang = defaultLanguage;

    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));

    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.parseTitle();
      }
    });
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
