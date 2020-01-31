import {Component, Input, OnDestroy, OnInit} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {VardaApiService} from '../../../../core/services/varda-api.service';
import {AllVakajarjestajaSearchDto, VardaVakajarjestaja} from '../../../../utilities/models/varda-vakajarjestaja.model';
import {PaosToimintaCreateDto, PaosToimipaikkaDto, PaosVakajarjestajaDto} from '../../../../utilities/models/dto/varda-paos-dto';
import {VardaToimipaikkaSearchDto} from '../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import {OrganisaatioIdentity, PaosCreateEvent, PaosToimintaService} from '../paos-toiminta.service';
import {Subscription} from 'rxjs';

@Component({
  selector: 'app-paos-add-paos-toiminta',
  templateUrl: './paos-add-paos-toiminta.component.html',
  styleUrls: ['./paos-add-paos-toiminta.component.css', '../varda-paos-management-generic-styles.css']
})
export class PaosAddPaosToimintaComponent implements OnInit, OnDestroy {
  @Input() isVakajarjestajaKunta: boolean;
  @Input() selectedVakajarjestaja: VardaVakajarjestaja;
  @Input() isVardaPaakayttaja: boolean;

  paosToimijaForm: FormGroup;
  vakajarjestajat: Array<PaosVakajarjestajaDto>;
  ignoredToimipaikkaIds: Set<string>;
  ignoredJarjestajaIds: Set<string>;

  isVakajarjestajatFetched: boolean;
  toimipaikatById: {[key: string]: Array<PaosToimipaikkaDto>};

  toimintaOrganisaatioSubscription: Subscription;
  toimintaOrganisaatioDeleteSubscription: Subscription;

  constructor(private apiService: VardaApiService,
              private paosToimintaService: PaosToimintaService) { }

  ngOnInit() {
    this.vakajarjestajat = [];
    this.toimipaikatById = {};
    this.ignoredToimipaikkaIds = new Set();
    this.ignoredJarjestajaIds = new Set();
    this.isVakajarjestajatFetched = false;
    const searchForm = new FormControl('', [Validators.required, Validators.minLength(3)]);
    this.paosToimijaForm = new FormGroup({
      search: searchForm,
    });
    this.toimintaOrganisaatioSubscription = this.paosToimintaService.toimintaOrganisaatioId$.subscribe(identity => {
      const id = identity.id;
      if (identity.type === PaosCreateEvent.Toimija) {
        this.ignoredJarjestajaIds.add(id);
      }
      if (identity.type === PaosCreateEvent.Toimipaikka) {
        this.ignoredToimipaikkaIds.add(id);
      }
    });
    this.toimintaOrganisaatioDeleteSubscription = this.paosToimintaService.toimintaDeletedOrganisaatioId$
      .subscribe(identity => {
        const id = identity.id;
        if (identity.type === PaosCreateEvent.Toimija) {
          this.ignoredJarjestajaIds.delete(id);
        }
        if (identity.type === PaosCreateEvent.Toimipaikka) {
          this.ignoredToimipaikkaIds.delete(id);
        }
      });
  }

  ngOnDestroy(): void {
    this.toimintaOrganisaatioSubscription.unsubscribe();
    this.toimintaOrganisaatioDeleteSubscription.unsubscribe();
  }

  searchToimija() {
    this.isVakajarjestajatFetched = false;
    this.vakajarjestajat = [];
    const searchDto: AllVakajarjestajaSearchDto = this.paosToimijaForm.value;
    // Yksityinen needs only kunta vakajarjestajat. Kunta needs all.
    searchDto.tyyppi = this.isVakajarjestajaKunta ? null : 'kunnallinen';
    this.apiService.getAllPagesSequentially(page => this.apiService.getAllPaosToimijat(searchDto, page))
      .subscribe({
        next: vakajarjestajat => {
          this.vakajarjestajat = vakajarjestajat;
          this.isVakajarjestajatFetched = true;
        },
        error: this.paosToimintaService.pushGenericErrorMessage,
      });
  }

  searchToimipaikat(vakajarjestaja: VardaVakajarjestaja) {
    const searchDto = new VardaToimipaikkaSearchDto();
    this.apiService.getAllPagesSequentially(page => this.apiService.getAllPaosToimipaikat(vakajarjestaja.id, searchDto, page))
      .subscribe(toimipaikat => {
        this.toimipaikatById = {[vakajarjestaja.id]: toimipaikat};
      });
  }

  toggleSearchToimipaikat(vakajarjestaja: VardaVakajarjestaja) {
    if (!this.isToimipaikkadata(vakajarjestaja.id)) {
        this.searchToimipaikat(vakajarjestaja);
    } else {
      this.toimipaikatById = {};
    }
  }

  addJarjestaja(vakajarjestaja: VardaVakajarjestaja) {
    const createDto = new PaosToimintaCreateDto();
    createDto.oma_organisaatio = VardaApiService.getVakajarjestajaUrlFromId(this.selectedVakajarjestaja.id);
    createDto.paos_organisaatio = VardaApiService.getVakajarjestajaUrlFromId(vakajarjestaja.id);
    this.apiService.createPaosToiminta(createDto).subscribe({
      next: paosToimintaDto => this.paosToimintaService.pushCreateEvent(PaosCreateEvent.Toimija, paosToimintaDto.paos_organisaatio),
      error: this.paosToimintaService.pushGenericErrorMessage,
    });
  }

  isToimipaikkadata(id: string) {
    return Object.keys(this.toimipaikatById).indexOf(`${id}`) !== -1;
  }

}
