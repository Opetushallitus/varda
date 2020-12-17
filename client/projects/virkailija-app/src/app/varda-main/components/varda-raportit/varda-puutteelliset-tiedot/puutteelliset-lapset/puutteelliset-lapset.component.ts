import { Component, Input } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { AbstractPuutteellisetHenkilotComponent } from '../puutteelliset-henkilot.abstract';


@Component({
  selector: 'app-varda-puutteelliset-lapset',
  templateUrl: './puutteelliset-lapset.component.html',
  styleUrls: ['./puutteelliset-lapset.component.css', '../varda-puutteelliset-tiedot.component.css']
})
export class VardaPuutteellisetLapsetComponent extends AbstractPuutteellisetHenkilotComponent<LapsiListDTO> {
  @Input() selectedVakajarjestaja: VardaVakajarjestajaUi;
  i18n = VirkailijaTranslations;

  constructor(
    private lapsiService: VardaLapsiService,
    private raportitService: VardaRaportitService,
    private snackBarService: VardaSnackBarService,
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
  ) {
    super(utilityService, translateService);

    this.subscriptions.push(this.lapsiService.listenLapsiListUpdate().subscribe(() => this.getHenkilot()));
  }

  getHenkilot(): void {
    this.henkilot = null;
    this.isLoading.next(true);
    this.raportitService.getLapsiErrorList(this.selectedVakajarjestaja.id, this.getFilter()).subscribe({
      next: henkiloData => {
        this.henkilot = henkiloData.results;
        this.searchFilter.count = henkiloData.count;
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    }).add(() => setTimeout(() => this.isLoading.next(false), 500));
  }

  openHenkilo(suhde: LapsiListDTO): void {
    this.openHenkiloForm.emit({ ...suhde, rooli: HenkiloRooliEnum.lapsi });
  }

  findHenkilo(henkilo: HenkiloListDTO) {
    this.lapsiService.getVakajarjestajaLapset(this.selectedVakajarjestaja.id, { search: henkilo.henkilo_oid }).subscribe({
      next: henkiloData => {
        const foundLapsi = henkiloData.results.find(lapsi => lapsi.henkilo_oid === henkilo.henkilo_oid);
        const foundSuhde = foundLapsi?.lapset.find(suhde => suhde.id === henkilo.lapsi_id);
        this.openHenkilo({...foundSuhde, henkilo_id: foundLapsi.id, henkilo_oid: foundLapsi.henkilo_oid });
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    });
  }
}
