import { Component, EventEmitter, Input, Output, SimpleChanges, OnInit } from '@angular/core';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { VardaLocalstorageWrapperService } from '../../../../core/services/varda-localstorage-wrapper.service';
import { VardaApiWrapperService } from '../../../../core/services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { Hallinnointijarjestelma } from '../../../../utilities/models/enums/hallinnointijarjestelma';
import { ModalEvent } from '../../../../shared/components/varda-modal-form/varda-modal-form.component';
import { VardaToimipaikkaMinimalDto, VardaToimipaikkaDTO } from '../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from '../../../../utilities/models/varda-user-access.model';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-varda-toimipaikka-selector',
  templateUrl: './varda-toimipaikka-selector.component.html',
  styleUrls: ['./varda-toimipaikka-selector.component.css']
})
export class VardaToimipaikkaSelectorComponent implements OnInit {
  @Input() toimijaAccess: UserAccess;
  @Output() changeToimipaikka = new EventEmitter<VardaToimipaikkaMinimalDto>(true);

  i18n = VirkailijaTranslations;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  activeToimipaikka: VardaToimipaikkaMinimalDto;
  formToimipaikka: VardaToimipaikkaMinimalDto;
  toimipaikkaData: VardaToimipaikkaDTO;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  toimipaikkaFormOpen: boolean;
  editToimipaikkaAction: boolean;
  hallinnointijarjestelmaTypes = Hallinnointijarjestelma;
  anyToimijaKatselija: boolean;

  confirmedToimipaikkaFormLeave = true;

  constructor(
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaLocalStorageWrapperService: VardaLocalstorageWrapperService
  ) {
    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    this.initToimipaikat();

    this.anyToimijaKatselija = this.toimijaAccess.lapsitiedot.katselija ||
      this.toimijaAccess.huoltajatiedot.katselija ||
      this.toimijaAccess.tyontekijatiedot.katselija ||
      this.toimijaAccess.taydennyskoulutustiedot.katselija;
  }

  initToimipaikat(): void {
    this.toimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().katselijaToimipaikat;

    if (this.toimipaikat.length === 0) {
      this.activeToimipaikka = null;
      this.changeToimipaikka.emit(this.activeToimipaikka);
      return;
    }

    if (this.toimipaikat.length === 1 || (!this.anyToimijaKatselija && this.toimipaikat.length > 0)) {
      this.activeToimipaikka = this.toimipaikat[0];
      this.vardaVakajarjestajaService.setSelectedToimipaikka(this.activeToimipaikka);
      this.changeToimipaikka.emit(this.activeToimipaikka);
      return;
    }

    this.toimipaikat = this.toimipaikat.sort((a, b) => {
      return a.nimi.toLowerCase().localeCompare(b.nimi.toLowerCase(), 'fi');
    });

    const activeToimipaikkaFromLocalStorage = this.vardaLocalStorageWrapperService.getFromLocalStorage('varda.activeToimipaikka');
    if (activeToimipaikkaFromLocalStorage) {
      const parsedToimipaikka = JSON.parse(activeToimipaikkaFromLocalStorage);
      if (parsedToimipaikka?.id) {
        this.activeToimipaikka = this.toimipaikat.find(toimipaikka => toimipaikka.id === parsedToimipaikka.id);
      }

    }

    if (!this.activeToimipaikka) {
      this.activeToimipaikka = null;
    }

    this.vardaVakajarjestajaService.setSelectedToimipaikka(this.activeToimipaikka);
    this.vardaVakajarjestajaService.setSelectedToimipaikkaSubject(this.activeToimipaikka);
    this.changeToimipaikka.emit(this.activeToimipaikka);
  }

  openToimipaikka(toimipaikka: VardaToimipaikkaMinimalDto): void {
    this.editToimipaikkaAction = true;
    this.formToimipaikka = toimipaikka;
    this.openToimipaikkaForm(toimipaikka.id);
  }

  toimipaikkaFormValuesChanged(hasChanged: boolean) {
    this.confirmedToimipaikkaFormLeave = !hasChanged;
  }

  openToimipaikkaForm(toimipaikka_id?: string): void {

    this.toimipaikkaData = null;

    if (toimipaikka_id) {
      this.vardaApiWrapperService.getToimipaikkaById(toimipaikka_id).subscribe(toimipaikkaData => {
        this.toimipaikkaData = toimipaikkaData;
        this.toimipaikkaFormOpen = true;
      });
    } else {
      this.toimipaikkaFormOpen = true;
    }
  }

  handleFormClose($eventObject: ModalEvent): void {
    if ($eventObject === ModalEvent.hidden) {
      this.toimipaikkaFormOpen = false;
      this.confirmedToimipaikkaFormLeave = true;
    }
  }

  addToimipaikka(): void {
    this.editToimipaikkaAction = false;
    this.formToimipaikka = null;
    this.openToimipaikkaForm();
  }

  updateToimipaikat(data: any): void {
    if (data.toimipaikka) {
      this.activeToimipaikka = data.toimipaikka;
      this.setToimipaikka(this.activeToimipaikka);
    }
  }

  setToimipaikka(toimipaikka: VardaToimipaikkaMinimalDto): void {
    if (toimipaikka) {
      this.vardaVakajarjestajaService.setSelectedToimipaikkaSubject(toimipaikka);
      this.vardaVakajarjestajaService.setSelectedToimipaikka(toimipaikka);
      this.vardaLocalStorageWrapperService.saveToLocalStorage('varda.activeToimipaikka', JSON.stringify(toimipaikka));
    }

    this.changeToimipaikka.emit(toimipaikka);
  }

}
