import { Component } from '@angular/core';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { AbstractHenkiloSectionComponent } from '../henkilo-section.abstract';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { extractCursor } from "../../../../utilities/helper-functions";

@Component({
    selector: 'app-varda-henkilosto-section',
    templateUrl: './varda-henkilosto-section.component.html',
    styleUrls: ['./varda-henkilosto-section.component.css', '../varda-main-frame.component.css'],
    standalone: false
})
export class VardaHenkilostoSectionComponent extends AbstractHenkiloSectionComponent {
  i18n = VirkailijaTranslations;
  constructor(
    private utilityService: VardaUtilityService,
    private henkilostoService: VardaHenkilostoApiService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService
  ) {
    super(utilityService);

    this.subscriptions.push(this.henkilostoService.listenHenkilostoListUpdate().subscribe(() => this.getHenkilot()));
  }

  getHenkilot(): void {
    this.henkilot = null;
    this.isLoading.next(true);
    const selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
    this.henkilostoService.getVakajarjestajaTyontekijat(selectedVakajarjestaja.id, this.getFilter()).subscribe({
      next: henkiloData => {
        this.henkilot = henkiloData.results;
        this.resultCount = henkiloData.count;
        this.nextCursor = extractCursor(henkiloData.next);
        this.prevCursor = extractCursor(henkiloData.previous);
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
