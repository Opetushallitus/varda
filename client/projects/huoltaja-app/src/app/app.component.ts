import { Component, OnInit, Inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Title } from '@angular/platform-browser';
import { LoadingHttpService } from 'varda-shared';
import { Observable } from 'rxjs/internal/Observable';
import { delay } from 'rxjs/internal/operators/delay';
import { DOCUMENT } from '@angular/common';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  isLoading: Observable<boolean>;

  constructor(
    private translateService: TranslateService,
    private titleService: Title,
    private loadingHttpService: LoadingHttpService,
    @Inject(DOCUMENT) private _document: any
  ) {
    const defaultLanguage = this.translateService.getBrowserLang() === 'sv' ? 'sv' : 'fi';
    this.translateService.setDefaultLang(defaultLanguage);
    this.translateService.use(defaultLanguage);
    this._document.documentElement.lang = defaultLanguage;
    this.isLoading = this.loadingHttpService.isLoading().pipe(delay(200));
  }

  ngOnInit() {
    this.translateService.get('page.title').subscribe(name => {
      this.titleService.setTitle(name);
    });
  }
}
