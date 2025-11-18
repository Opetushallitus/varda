import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Observable, Subscription } from 'rxjs';

@Component({
  selector: 'app-tiedonsiirto-filter',
  templateUrl: './tiedonsiirto-filter.component.html',
  styleUrls: ['./tiedonsiirto-filter.component.css']
})
export class TiedonsiirtoFilterComponent implements OnInit, OnDestroy {
  @Input() oph: boolean;
  vakajarjestajat$: Observable<Array<VardaVakajarjestajaUi>>;

  i18n = VirkailijaTranslations;
  selectedVakajarjestajat: Array<number>;
  subscriptions: Array<Subscription> = [];

  constructor(
    private raportitService: VardaRaportitService,
    private vakajarjestajaService: VardaVakajarjestajaService,
  ) { }

  ngOnInit(): void {
    if (this.oph) {
      this.vakajarjestajat$ = this.vakajarjestajaService.getVakajarjestajat();
    }

    this.subscriptions.push(
      this.raportitService.getSelectedVakajarjestajat().subscribe(selectedVakajarjetajat =>
        this.selectedVakajarjestajat = selectedVakajarjetajat || [this.vakajarjestajaService.getSelectedVakajarjestaja().id]
      )
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  saveSelectedVakajarjestajat(selectedVakajarjestajat: Array<number>) {
    this.raportitService.setSelectedVakajarjestajat(selectedVakajarjestajat);
  }
}
