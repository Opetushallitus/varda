import { Component, OnDestroy, OnInit } from '@angular/core';
import { PaosToimijaInternalDto, PaosToimipaikkatietoDto } from '../../../../utilities/models/dto/varda-paos-dto';
import { filter } from 'rxjs/operators';
import { Subscription } from 'rxjs';
import { AbstractPaosListToimintainfoComponentDirective } from './abstract-paos-list-toimintainfo-component';
import { PaosCreateEvent, PaosToimintaService } from '../paos-toiminta.service';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { VardaPaosApiService } from 'projects/virkailija-app/src/app/core/services/varda-paos-api.service';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';

@Component({
  selector: 'app-paos-added-toimipaikat',
  templateUrl: './paos-added-toimipaikat.component.html',
  styleUrls: ['./paos-added-toimijat.component.css', '../varda-paos-management-generic-styles.css'],
  animations: [
    trigger('fadeOut', [
      state('void', style({
        opacity: 0,
      })),
      transition('* => void', animate(1500))
    ])
  ]
})
export class PaosAddedToimipaikatComponent extends AbstractPaosListToimintainfoComponentDirective<PaosToimipaikkatietoDto> implements OnInit, OnDestroy {
  private createEventSubscription: Subscription;
  i18n = VirkailijaTranslations;
  highlighted: Array<string>;
  toimipaikatByToimija: Array<PaosToimijaInternalDto>;
  filteredToiminnat: Array<PaosToimijaInternalDto>;
  openToimija: number;
  openTallennusvastuu: number;
  changedTallennusvastuu: { toimijaId: number, newTallentaja: number, };

  apiServiceMethod = () => this.paosService.getPaosToimipaikat(this.selectedVakajarjestaja.id);
  pushToimintaOrganisaatioId = (paosToiminta: PaosToimipaikkatietoDto) => this.paosToimintaService.pushToimintaOrganisaatio(paosToiminta.toimipaikka_id, PaosCreateEvent.Toimipaikka);

  constructor(
    private paosService: VardaPaosApiService,
    private paosToimintaService: PaosToimintaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private vakajarjestajaService: VardaVakajarjestajaService
  ) {
    super();
  }

  ngOnInit() {
    this.highlighted = [];
    this.toimipaikatByToimija = [];
    this.filteredToiminnat = [];
    this.changedTallennusvastuu = { toimijaId: null, newTallentaja: null };
    super.ngOnInit();
    this.createEventSubscription = this.paosToimintaService.createEvents$.pipe(
      filter(event => event === PaosCreateEvent.Toimipaikka)
    ).subscribe({
      next: event => {
        this.highlighted = this.paosToimintaService.createdPaosToimintaOrganisaatioUrl;
        this.showAndHideSuccessMessage();
        this.getPaosToiminnat();
      },
      error: this.paosToimintaService.pushGenericErrorMessage,
    });

  }

  ngOnDestroy(): void {
    this.createEventSubscription.unsubscribe();
  }

  getPaosToiminnatErrorHook(err) {
    this.paosToimintaService.pushGenericErrorMessage(err);
  }

  getPaosToiminnatOnCompleteHook() {
    const groupObject = this.paosToiminnat.reduce(((accumulator, currentToimipaikkatietoDto) => {
      if (!accumulator[currentToimipaikkatietoDto.toimija_id]) {
        const toimija = new PaosToimijaInternalDto();
        toimija.toimijaId = currentToimipaikkatietoDto.toimija_id;
        toimija.toimijaOID = currentToimipaikkatietoDto.toimija_organisaatio_oid;
        toimija.toimijaNimi = currentToimipaikkatietoDto.toimija_nimi;
        toimija.toimijaUrl = currentToimipaikkatietoDto.toimija_url;
        toimija.toimijaYTunnus = currentToimipaikkatietoDto.toimija_y_tunnus;
        toimija.toimipaikat = [];
        toimija.paosOikeus = currentToimipaikkatietoDto.paos_oikeus;
        accumulator[currentToimipaikkatietoDto.toimija_id] = toimija;
      }
      const toimipaikka = { ...currentToimipaikkatietoDto };
      accumulator[currentToimipaikkatietoDto.toimija_id].toimipaikat.push(toimipaikka);
      return accumulator;
    }), {});

    this.toimipaikatByToimija = Object.values(groupObject);
    this.filteredToiminnat = [...this.toimipaikatByToimija];
    this.filteredToiminnat.sort((a: PaosToimijaInternalDto, b: PaosToimijaInternalDto) => a.toimijaNimi.localeCompare(b.toimijaNimi, 'fi'));
    this.filteredToiminnat.forEach(toimija =>
      toimija.toimipaikat.sort((a: PaosToimipaikkatietoDto, b: PaosToimipaikkatietoDto) =>
        a.toimipaikka_nimi.localeCompare(b.toimipaikka_nimi, 'fi')
      )
    );
  }

  filterToimintaInfo(searchText: string) {
    this.filteredToiminnat = this.toimipaikatByToimija.filter(paosToimija => {
      const nimi = paosToimija.toimijaNimi;
      return nimi.toLowerCase().includes(searchText.toLowerCase());
    });
  }

  deletePaosToiminta() {
    const openToimija = (this.filteredToiminnat || []).filter(_paostoiminta => _paostoiminta.toimijaId === this.openToimija)[0];
    if (openToimija && openToimija.toimipaikat.length === 1) {
      this.openToimija = null;
    }
    this.paosService.deletePaosToiminta(`${this.paosToimintaToDelete.paos_toiminta_id}`).subscribe({
      next: value => {
        this.paosToimintaService.pushDeletedToimintaOrganisaatio(this.paosToimintaToDelete.toimipaikka_id, PaosCreateEvent.Toimipaikka);
        this.clearTallenusvastuu();
        this.getPaosToiminnat();
      },
      error: this.paosToimintaService.pushGenericErrorMessage,
    });
  }

  toggleToimija(toimija_id: number) {
    this.openToimija = this.openToimija === toimija_id ? null : toimija_id;
    this.clearTallenusvastuu();
  }

  isToimijaHighlighted(highlighted: Array<string>, paosToiminta: PaosToimijaInternalDto) {
    return paosToiminta.toimipaikat
      .map(toimipaikka => toimipaikka.toimipaikka_url)
      .filter(toimipaikka => highlighted.includes(toimipaikka))
      .length;
  }

  changeTallennusvastuu(tallennusvastuuId: string, paosToiminta: PaosToimijaInternalDto) {
    const newTallentaja = parseInt(tallennusvastuuId) === this.selectedVakajarjestaja.id ? this.selectedVakajarjestaja.id : paosToiminta.toimijaId;
    this.changedTallennusvastuu = {
      toimijaId: paosToiminta.toimijaId,
      newTallentaja: newTallentaja,
    };
  }

  saveTallennusvastuu(paosToiminta: PaosToimijaInternalDto) {
    if (this.openTallennusvastuu === paosToiminta.toimijaId && this.changedTallennusvastuu.toimijaId === paosToiminta.toimijaId) {
      this.paosService.updatePaosOikeus(paosToiminta.paosOikeus.id, this.changedTallennusvastuu.newTallentaja)
        .subscribe({
          next: value => {
            this.clearTallenusvastuu();
            this.getPaosToiminnat();

            this.vakajarjestajaApiService.getToimipaikat(this.selectedVakajarjestaja.id).subscribe(toimipaikat => this.vakajarjestajaService.setToimipaikat(toimipaikat));
          },
          error: this.paosToimintaService.pushGenericErrorMessage,
        });
    }
  }

  private clearTallenusvastuu() {
    this.openTallennusvastuu = null;
    this.changedTallennusvastuu = { toimijaId: null, newTallentaja: null };
  }

  isTallentajaChanged(paosToiminta: PaosToimijaInternalDto) {
    return !this.changedTallennusvastuu.newTallentaja || this.changedTallennusvastuu.newTallentaja === paosToiminta.paosOikeus.tallentaja_organisaatio_id;
  }
}
