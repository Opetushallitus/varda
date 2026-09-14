import { Component, OnInit } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { MatomoService } from 'varda-shared';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';

@Component({
    selector: 'app-varda-body',
    templateUrl: './varda-body.component.html',
    styleUrls: ['./varda-body.component.css'],
    standalone: false
})
export class VardaBodyComponent implements OnInit {
  i18n = VirkailijaTranslations;
  virkailijaRaamit: boolean;
  constructor(
    private vardaUtilityService: VardaUtilityService,
    private matomo: MatomoService
  ) { }

  ngOnInit(): void {
    this.initRaamit();
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
      } else {
        const [productionID, qaID] = [29, 30];
        this.matomo.initMatomo(window.location.hostname.includes('testiopintopolku') ? qaID : productionID);
      }
    }
  }

}
