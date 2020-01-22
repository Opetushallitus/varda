import {Component, Input, OnInit} from '@angular/core';
import {VardaToimipaikkaDTO} from '../../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import {PaosToimintaCreateDto, PaosToimipaikkaDto} from '../../../../../utilities/models/dto/varda-paos-dto';
import {VardaApiService} from '../../../../../core/services/varda-api.service';
import {VardaVakajarjestaja} from '../../../../../utilities/models/varda-vakajarjestaja.model';
import {OrganisaatioIdentity, PaosCreateEvent, PaosToimintaService} from '../../paos-toiminta.service';

@Component({
  selector: 'app-paos-add-toiminta-list',
  templateUrl: './paos-add-toiminta-list.component.html',
  styleUrls: ['./paos-add-toiminta-list.component.css', '../../varda-paos-management-generic-styles.css']
})
export class PaosAddToimintaListComponent implements OnInit {
  @Input() toimipaikat: Array<PaosToimipaikkaDto>;
  @Input() selectedVakajarjestaja: VardaVakajarjestaja;
  @Input() ignoredIds: Set<string>;
  filteredToimipaikat: Array<VardaToimipaikkaDTO>;

  constructor(private apiService: VardaApiService,
              private paosToimintaService: PaosToimintaService) { }

  ngOnInit() {
    this.filteredToimipaikat = this.toimipaikat ? [...this.toimipaikat] : [];
  }

  addToimipaikka(toimipaikka: VardaToimipaikkaDTO) {
    const createDto = new PaosToimintaCreateDto();
    createDto.oma_organisaatio = VardaApiService.getVakajarjestajaUrlFromId(this.selectedVakajarjestaja.id);
    createDto.paos_toimipaikka = VardaApiService.getToimipaikkaUrlFromId(toimipaikka.id);
    this.apiService.createPaosToiminta(createDto).subscribe({
      next: paosToimintaDto => this.paosToimintaService.pushCreateEvent(PaosCreateEvent.Toimipaikka, paosToimintaDto.paos_toimipaikka),
      error: this.paosToimintaService.pushGenericErrorMessage,
    });
  }

  filterToimipaikat(searchText: string) {
    const toimipaikat = this.toimipaikat ? [...this.toimipaikat] : [];
    this.filteredToimipaikat = toimipaikat
      .filter(toimipaikka => toimipaikka.organisaatio_oid === searchText
        || toimipaikka.nimi && toimipaikka.nimi.toLowerCase().includes(searchText.toLowerCase()));
  }
}
