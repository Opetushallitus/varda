import { Component, OnDestroy, OnInit } from '@angular/core';
import { AbstractPaosListToimintainfoComponentDirective } from './abstract-paos-list-toimintainfo-component';
import { PaosToimintatietoDto } from '../../../../utilities/models/dto/varda-paos-dto';
import { PaosCreateEvent, PaosToimintaService } from '../paos-toiminta.service';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { VardaPaosApiService } from 'projects/virkailija-app/src/app/core/services/varda-paos-api.service';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-paos-added-toimijat',
  templateUrl: './paos-added-toimijat.component.html',
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
export class PaosAddedToimijatComponent extends AbstractPaosListToimintainfoComponentDirective<PaosToimintatietoDto> implements OnInit, OnDestroy {
  private createEventSubscription: Subscription;
  i18n = VirkailijaTranslations;
  highlighted: Array<string>;
  openToimija: number;
  filteredToiminnat: Array<PaosToimintatietoDto>;
  apiServiceMethod = () => this.paosService.getPaosToimijat(this.selectedVakajarjestaja.id);
  pushToimintaOrganisaatioId = paosToiminta => this.paosToimintaService.pushToimintaOrganisaatio(paosToiminta.vakajarjestaja_id, PaosCreateEvent.Toimija);

  constructor(
    private paosService: VardaPaosApiService,
    private paosToimintaService: PaosToimintaService,
  ) {
    super();
  }

  ngOnInit() {
    super.ngOnInit();

    this.highlighted = [];
    this.openToimija = null;
    this.createEventSubscription = this.paosToimintaService.createEvents$.pipe(
      filter(event => event === PaosCreateEvent.Toimija)
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

  deletePaosToiminta() {
    this.openToimija = null;
    this.paosService.deletePaosToiminta(`${this.paosToimintaToDelete.paos_toiminta_id}`).subscribe({
      next: value => {
        this.paosToimintaService.pushDeletedToimintaOrganisaatio(this.paosToimintaToDelete.vakajarjestaja_id, PaosCreateEvent.Toimija);
        this.getPaosToiminnat();
      },
      error: this.paosToimintaService.pushGenericErrorMessage,
    });
  }

  toggleToimija(id: number) {
    this.openToimija = this.openToimija === id ? null : id;
  }

  getPaosToiminnatOnCompleteHook() {
    this.paosToiminnat.sort((a: PaosToimintatietoDto, b: PaosToimintatietoDto) => a.vakajarjestaja_nimi.localeCompare(b.vakajarjestaja_nimi, 'fi'));
    this.filteredToiminnat = [...this.paosToiminnat];
  }

  getPaosToiminnatErrorHook(err) {
    this.paosToimintaService.pushGenericErrorMessage(err);
  }

  filterToimintaInfo(searchText: string) {
    this.filteredToiminnat = this.paosToiminnat.filter(paosToimija => {
      const nimi = paosToimija.vakajarjestaja_nimi;
      return nimi.toLowerCase().includes(searchText.toLowerCase());
    });
  }
}
