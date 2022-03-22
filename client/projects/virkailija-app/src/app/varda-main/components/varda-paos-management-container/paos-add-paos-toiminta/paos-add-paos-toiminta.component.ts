import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { AllVakajarjestajaSearchDto, VardaVakajarjestaja } from '../../../../utilities/models/varda-vakajarjestaja.model';
import { PaosToimintaCreateDto, PaosToimipaikkaDto, PaosVakajarjestajaDto } from '../../../../utilities/models/dto/varda-paos-dto';
import { PaosCreateEvent, PaosToimintaService } from '../paos-toiminta.service';
import { Subscription } from 'rxjs';
import { VardaPaosApiService } from 'projects/virkailija-app/src/app/core/services/varda-paos-api.service';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-paos-add-paos-toiminta',
  templateUrl: './paos-add-paos-toiminta.component.html',
  styleUrls: ['./paos-add-paos-toiminta.component.css', '../varda-paos-management-generic-styles.css']
})
export class PaosAddPaosToimintaComponent implements OnInit, OnDestroy {
  @Input() isVakajarjestajaKunta: boolean;
  @Input() selectedVakajarjestaja: VardaVakajarjestaja;
  @Input() isVardaPaakayttaja: boolean;

  i18n = VirkailijaTranslations;

  paosToimijaForm: FormGroup;
  vakajarjestajat: Array<PaosVakajarjestajaDto>;
  ignoredToimipaikkaIds: Set<number>;
  ignoredJarjestajaIds: Set<number>;

  isVakajarjestajatFetched: boolean;
  toimipaikatById: { [key: number]: Array<PaosToimipaikkaDto> };

  toimintaOrganisaatioSubscription: Subscription;
  toimintaOrganisaatioDeleteSubscription: Subscription;

  constructor(
    private paosService: VardaPaosApiService,
    private paosToimintaService: PaosToimintaService
  ) { }

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

    this.paosService.getAllPaosToimijat(searchDto).subscribe({
      next: vakajarjestajat => {
        this.vakajarjestajat = vakajarjestajat.sort((a, b) => a.nimi.localeCompare(b.nimi, 'fi'));
        this.isVakajarjestajatFetched = true;
      },
      error: this.paosToimintaService.pushGenericErrorMessage,
    });
  }

  searchToimipaikat(vakajarjestaja: VardaVakajarjestaja) {
    const searchDto = {};
    this.paosService.getAllPaosToimipaikat(vakajarjestaja.id, searchDto).subscribe({
      next: toimipaikat => {
        this.toimipaikatById = { [vakajarjestaja.id]: toimipaikat.sort((a, b) => a.nimi.localeCompare(b.nimi, 'fi')) };
      },
      error: err => console.log(err)
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
    this.paosService.createPaosToiminta(createDto).subscribe({
      next: paosToimintaDto => this.paosToimintaService.pushCreateEvent(PaosCreateEvent.Toimija, paosToimintaDto.paos_organisaatio),
      error: this.paosToimintaService.pushGenericErrorMessage,
    });
  }

  isToimipaikkadata(id: number) {
    return Object.keys(this.toimipaikatById).indexOf(`${id}`) !== -1;
  }

}
