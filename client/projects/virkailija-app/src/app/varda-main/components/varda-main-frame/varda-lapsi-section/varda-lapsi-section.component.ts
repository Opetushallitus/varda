import { Component } from '@angular/core';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { HenkiloSearchFilter, AbstractHenkiloSectionComponent } from '../henkilo-section.abstract';
import { VardaApiService } from 'projects/virkailija-app/src/app/core/services/varda-api.service';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';


@Component({
  selector: 'app-varda-lapsi-section',
  templateUrl: './varda-lapsi-section.component.html',
  styleUrls: ['./varda-lapsi-section.component.css', '../varda-main-frame.component.css']
})
export class VardaLapsiSectionComponent extends AbstractHenkiloSectionComponent {
  i18n = VirkailijaTranslations;
  constructor(
    private apiService: VardaApiService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private lapsiService: VardaLapsiService
  ) {
    super(apiService);

    this.subscriptions.push(this.lapsiService.listenLapsiListUpdate().subscribe(() => this.getHenkilot()));
  }

  getHenkilot(): void {
    this.henkilot = null;
    this.isLoading.next(true);

    const selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.lapsiService.getVakajarjestajaLapset(selectedVakajarjestaja.id, this.getFilter()).subscribe({
      next: henkiloData => {
        this.henkilot = henkiloData.results;
        this.searchFilter.count = henkiloData.count;
      },
      error: (err) => console.error(err)
    }).add(() => setTimeout(() => this.isLoading.next(false), 500));

  }

  addHenkilo(): void {
    this.openHenkiloForm.emit({ rooli: HenkiloRooliEnum.lapsi });
  }

  openHenkilo(suhde: LapsiListDTO): void {
    this.openHenkiloForm.emit({ ...suhde, rooli: HenkiloRooliEnum.lapsi });
  }
}
