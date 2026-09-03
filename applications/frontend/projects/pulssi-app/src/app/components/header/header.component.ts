import { Component, Inject, OnInit, DOCUMENT } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

import { BehaviorSubject } from 'rxjs';
import { PulssiTranslations } from '../../../assets/i18n/translations.enum';
import { ResponsiveService } from 'varda-shared';

@Component({
    selector: 'app-header',
    templateUrl: './header.component.html',
    styleUrls: ['./header.component.css'],
    standalone: false
})
export class HeaderComponent implements OnInit {
  translations = PulssiTranslations;
  currentLang: string;
  isSmall: BehaviorSubject<boolean>;

  constructor(private translateService: TranslateService,
              private responsiveService: ResponsiveService,
              @Inject(DOCUMENT) private document: Document) { }

  ngOnInit(): void {
    this.currentLang = this.translateService.currentLang;
    this.isSmall = this.responsiveService.getIsSmall();
  }

  changeLanguage(lang: string) {
    if (this.currentLang !== lang) {
      this.translateService.use(lang);
      this.document.documentElement.lang = lang;
      this.currentLang = lang;
    }
  }
}
