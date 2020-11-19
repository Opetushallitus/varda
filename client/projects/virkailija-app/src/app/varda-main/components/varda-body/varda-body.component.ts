import { Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { NgcCookieConsentService } from 'ngx-cookieconsent';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { switchMap } from 'rxjs/operators';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';

@Component({
  selector: 'app-varda-body',
  templateUrl: './varda-body.component.html',
  styleUrls: ['./varda-body.component.css']
})
export class VardaBodyComponent implements OnInit {
  i18n = VirkailijaTranslations;
  virkailijaRaamit: boolean;
  constructor(
    private vardaUtilityService: VardaUtilityService,
    private translateService: TranslateService,
    private ccService: NgcCookieConsentService,
  ) { }

  ngOnInit(): void {
    this.initRaamit();
    this.initGDPR();
  }

  initRaamit() {
    const virkailijaRaamitUrl = this.vardaUtilityService.getVirkailijaRaamitUrl(window.location.hostname);
    if (virkailijaRaamitUrl) {
      this.virkailijaRaamit = true;
      const node = document.createElement('script');
      node.src = virkailijaRaamitUrl;
      node.type = 'text/javascript';
      node.async = true;
      document.getElementsByTagName('head')[0].appendChild(node);

      if (!window.location.hostname.includes('opintopolku.fi')) {
        setTimeout(() => window.document.dispatchEvent(new Event('DOMContentLoaded')), 500);
      }
    }
  }


  initGDPR() {
    this.translateService.get([this.i18n.cookie_popup_message]).subscribe((translations) => {
      this.handleCookies(translations);
    });

    this.translateService.onLangChange.pipe(
      switchMap(() => this.translateService.get([this.i18n.cookie_popup_message]))
    ).subscribe((translations) => {
      this.handleCookies(translations);
    });
  }

  private handleCookies(translations: any) {
    this.ccService.getConfig().content = this.ccService.getConfig().content || {};
    // Override default messages with the translated ones
    this.ccService.getConfig().content.message = translations[this.i18n.cookie_popup_message];
    this.ccService.destroy();
    this.ccService.init(this.ccService.getConfig()); // update config with translated messages
  }
}
