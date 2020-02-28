import {Component, OnDestroy, OnInit} from '@angular/core';
import {PaosToimijaInternalDto, PaosToimipaikkatietoDto} from '../../../../utilities/models/dto/varda-paos-dto';
import {VardaApiService} from '../../../../core/services/varda-api.service';
import {filter} from 'rxjs/operators';
import {Subscription} from 'rxjs';
import {AbstractPaosListToimintainfoComponent} from './abstract-paos-list-toimintainfo-component';
import {PaosCreateEvent, PaosToimintaService} from '../paos-toiminta.service';
import {animate, state, style, transition, trigger} from '@angular/animations';

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
export class PaosAddedToimipaikatComponent extends AbstractPaosListToimintainfoComponent<PaosToimipaikkatietoDto> implements OnInit, OnDestroy {
  private createEventSubscription: Subscription;
  highlighted: Array<string>;
  toimipaikatByToimija: Array<PaosToimijaInternalDto>;
  filteredToiminnat: Array<PaosToimijaInternalDto>;
  openToimija: string;
  openTallennusvastuu: string;
  changedTallennusvastuu: {toimijaId: string, newTallentaja: string, };

  private _apiCallMethod = (page: number) => this.apiService.getPaosToimipaikat(this.selectedVakajarjestaja.id, page);
  apiServiceMethod = () => this.apiService.getAllPagesSequentially<PaosToimipaikkatietoDto>(this._apiCallMethod);

  pushToimintaOrganisaatioId = (paosToiminta: PaosToimipaikkatietoDto) => this.paosToimintaService.pushToimintaOrganisaatio(paosToiminta.toimipaikka_id, PaosCreateEvent.Toimipaikka);

  constructor(private apiService: VardaApiService,
              private paosToimintaService: PaosToimintaService) {
    super();
  }

  ngOnInit() {
    this.highlighted = [];
    this.toimipaikatByToimija = [];
    this.filteredToiminnat = [];
    this.openToimija = '';
    this.openTallennusvastuu = '';
    this.changedTallennusvastuu = {toimijaId: '', newTallentaja: ''};
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
        toimija.toimijaNimi = currentToimipaikkatietoDto.toimija_nimi;
        toimija.toimijaUrl = currentToimipaikkatietoDto.toimija_url;
        toimija.toimijaYTunnus = currentToimipaikkatietoDto.toimija_y_tunnus;
        toimija.toimipaikat = [];
        toimija.paosOikeus = currentToimipaikkatietoDto.paos_oikeus;
        accumulator[currentToimipaikkatietoDto.toimija_id] = toimija;
      }
      const toimipaikka = {...currentToimipaikkatietoDto};
      accumulator[currentToimipaikkatietoDto.toimija_id].toimipaikat.push(toimipaikka);
      return accumulator;
    }), {});
    this.toimipaikatByToimija = Object.values(groupObject);
    this.filteredToiminnat = [...this.toimipaikatByToimija];
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
      this.openToimija = '';
    }
    this.apiService.deletePaosToiminta(`${this.paosToimintaToDelete.paos_toiminta_id}`).subscribe({
      next: value => {
        this.paosToimintaService.pushDeletedToimintaOrganisaatio(this.paosToimintaToDelete.toimipaikka_id, PaosCreateEvent.Toimipaikka);
        this.clearTallenusvastuu();
        this.getPaosToiminnat();
      },
      error: this.paosToimintaService.pushGenericErrorMessage,
    });
  }

  toggleToimija(toimija_id: string) {
    this.openToimija = this.openToimija === toimija_id ? '' : toimija_id;
    this.clearTallenusvastuu();
  }

  isToimijaHighlighted(highlighted: Array<string>, paosToiminta: PaosToimijaInternalDto) {
    return paosToiminta.toimipaikat
      .map(toimipaikka => toimipaikka.toimipaikka_url)
      .filter(toimipaikka => highlighted.includes(toimipaikka))
      .length;
  }

  changeTallennusvastuu(tallennusvastuuKey: string, paosToiminta: PaosToimijaInternalDto) {
    const newTallentaja = tallennusvastuuKey === 'label.tallentaja' ? this.selectedVakajarjestaja.id : paosToiminta.toimijaId;
    this.changedTallennusvastuu = {
      toimijaId: paosToiminta.toimijaId,
      newTallentaja: newTallentaja,
    };
  }

  saveTallennusvastuu(paosToiminta: PaosToimijaInternalDto) {
    if (this.openTallennusvastuu === paosToiminta.toimijaId && this.changedTallennusvastuu.toimijaId === paosToiminta.toimijaId) {
      this.apiService.updatePaosOikeus(paosToiminta.paosOikeus.id, this.changedTallennusvastuu.newTallentaja)
        .subscribe({
          next: value => {
            this.clearTallenusvastuu();
            this.getPaosToiminnat();
          },
          error: this.paosToimintaService.pushGenericErrorMessage,
        });
    }
  }

  private clearTallenusvastuu() {
    this.openTallennusvastuu = '';
    this.changedTallennusvastuu = {toimijaId: '', newTallentaja: ''};
  }

  isTallentajaChanged(paosToiminta: PaosToimijaInternalDto) {
    return !this.changedTallennusvastuu.newTallentaja || parseInt(this.changedTallennusvastuu.newTallentaja) === paosToiminta.paosOikeus.tallentaja_organisaatio_id;
  }
}
