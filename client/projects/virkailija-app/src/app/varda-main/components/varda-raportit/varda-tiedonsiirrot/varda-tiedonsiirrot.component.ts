import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';



@Component({
  selector: 'app-varda-tiedonsiirrot',
  templateUrl: './varda-tiedonsiirrot.component.html',
  styleUrls: [
    './varda-tiedonsiirrot.component.css',
    '../varda-raportit.component.css'
  ]
})
export class VardaTiedonsiirrotComponent implements OnDestroy {
  i18n = VirkailijaTranslations;
  activeLink: string;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  subscriptions: Array<Subscription> = [];

  constructor(
    private router: Router,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private raportitService: VardaRaportitService,
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(
        (navigation: NavigationEnd) => this.setPage()
      ),
    );

    this.setPage();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.raportitService.setSelectedVakajarjestajat(null);
  }

  setPage() {
    this.activeLink = this.router.url.split('?').shift().split('/').pop();
  }
}
