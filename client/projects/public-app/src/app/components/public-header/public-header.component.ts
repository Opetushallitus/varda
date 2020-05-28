import { Component, Inject, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { DOCUMENT } from '@angular/common';
import { PublicResponsiveService } from '../../services/public-responsive.service';
import { BehaviorSubject } from 'rxjs';

@Component({
  selector: 'app-public-header',
  templateUrl: './public-header.component.html',
  styleUrls: ['./public-header.component.css']
})
export class PublicHeaderComponent implements OnInit {
  currentLang: String;
  isSmall: BehaviorSubject<boolean>;

  constructor(private translateService: TranslateService,
              private responsiveService: PublicResponsiveService,
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
