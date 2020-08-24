import { Component } from '@angular/core';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { AbstractHenkiloSectionComponent } from '../henkilo-section.abstract';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaApiService } from 'projects/virkailija-app/src/app/core/services/varda-api.service';

@Component({
  selector: 'app-varda-henkilosto-section',
  templateUrl: './varda-henkilosto-section.component.html',
  styleUrls: ['./varda-henkilosto-section.component.css', '../varda-main-frame.component.css']
})
export class VardaHenkilostoSectionComponent extends AbstractHenkiloSectionComponent {
  i18n = VirkailijaTranslations;
  constructor(
    private apiService: VardaApiService,
    private henkilostoService: VardaHenkilostoApiService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService
  ) {
    super(apiService);

    this.subscriptions.push(this.henkilostoService.listenHenkilostoListUpdate().subscribe(() => this.getHenkilot()));
  }

  getHenkilot(): void {
    this.henkilot = null;
    this.isLoading.next(true);
    const selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
    this.henkilostoService.getVakajarjestajaTyontekijat(selectedVakajarjestaja.id, this.getFilter()).subscribe({
      next: henkiloData => {
        this.henkilot = henkiloData.results;
        this.searchFilter.count = henkiloData.count;
      },
      error: (err) => console.error(err)
    }).add(() => setTimeout(() => this.isLoading.next(false), 500));
  }

  addHenkilo(): void {
    this.openHenkiloForm.emit({ rooli: HenkiloRooliEnum.tyontekija });
  }

  openHenkilo(suhde: TyontekijaListDTO): void {
    this.openHenkiloForm.emit({ ...suhde, rooli: HenkiloRooliEnum.tyontekija });
  }

}
