import { Component } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaUtilityService } from 'projects/virkailija-app/src/app/core/services/varda-utility.service';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { AbstractPuutteellisetComponent } from '../abstract-puutteelliset.component';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';

@Component({
  selector: 'app-varda-puutteelliset-tyontekijat',
  templateUrl: './puutteelliset-tyontekijat.component.html',
  styleUrls: ['./puutteelliset-tyontekijat.component.css', '../varda-puutteelliset-tiedot.component.css']
})
export class VardaPuutteellisetTyontekijatComponent extends AbstractPuutteellisetComponent<HenkiloListDTO, TyontekijaListDTO> {
  i18n = VirkailijaTranslations;
  henkilot: Array<HenkiloListDTO>;

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private raportitService: VardaRaportitService,
    private snackBarService: VardaSnackBarService,
    protected utilityService: VardaUtilityService,
    protected translateService: TranslateService,
    vakajarjestajaService: VardaVakajarjestajaService,
  ) {
    super(utilityService, translateService, vakajarjestajaService);
    this.subscriptions.push(this.henkilostoService.listenHenkilostoListUpdate().subscribe(() => this.getErrors()));
  }

  getErrors(): void {
    this.henkilot = null;
    this.isLoading.next(true);

    this.raportitService.getTyontekijaErrorList(this.selectedVakajarjestaja.id, this.getFilter()).subscribe({
      next: henkiloData => {
        this.henkilot = henkiloData.results;
        this.searchFilter.count = henkiloData.count;
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    }).add(() => setTimeout(() => this.isLoading.next(false), 500));
  }

  openForm(suhde: TyontekijaListDTO): void {
    this.openHenkiloForm.emit({ ...suhde, rooli: HenkiloRooliEnum.tyontekija });
  }

  findInstance(henkilo: HenkiloListDTO) {
    this.henkilostoService.getVakajarjestajaTyontekijat(this.selectedVakajarjestaja.id, { search: henkilo.henkilo_oid }).subscribe({
      next: henkiloData => {
        const foundTyontekija = henkiloData.results.find(tyontekija => tyontekija.henkilo_oid === henkilo.henkilo_oid);
        const foundSuhde = foundTyontekija?.tyontekijat.find(suhde => suhde.id === henkilo.tyontekija_id);
        this.openForm({ ...foundSuhde, henkilo_id: foundTyontekija.id, henkilo_oid: foundTyontekija.henkilo_oid });
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    });
  }
}
