import { Component, EventEmitter, Input, Output, OnInit, OnDestroy } from '@angular/core';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { Hallinnointijarjestelma } from '../../../../utilities/models/enums/hallinnointijarjestelma';
import { ModalEvent } from '../../../../shared/components/varda-modal-form/varda-modal-form.component';
import { UserAccess } from '../../../../utilities/models/varda-user-access.model';
import { VardaToimipaikkaDTO, VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { ToimipaikkaChange } from '../varda-main-frame.component';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaCookieEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/varda-cookie.enum';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-varda-toimipaikka-selector',
  templateUrl: './varda-toimipaikka-selector.component.html',
  styleUrls: ['./varda-toimipaikka-selector.component.css']
})
export class VardaToimipaikkaSelectorComponent implements OnInit, OnDestroy {
  @Input() toimijaAccess: UserAccess;
  @Output() changeToimipaikka = new EventEmitter<ToimipaikkaChange>(true);

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
  subscriptions: Array<Subscription> = [];
  confirmedToimipaikkaFormLeave = true;

  constructor(
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
  ) {
    this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    this.anyToimijaKatselija = this.toimijaAccess.lapsitiedot.katselija ||
      this.toimijaAccess.huoltajatiedot.katselija ||
      this.toimijaAccess.tyontekijatiedot.katselija ||
      this.toimijaAccess.taydennyskoulutustiedot.katselija;

    this.subscriptions.push(
      this.vardaVakajarjestajaService.getToimipaikat().subscribe({
        next: toimipaikat => this.initToimipaikat(this.vardaVakajarjestajaService.getFilteredToimipaikat().katselijaToimipaikat),
        error: err => console.error(err)
      })
    );
  }

  initToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>): void {
    this.toimipaikat = toimipaikat;
    if (this.toimipaikat.length === 0) {
      this.activeToimipaikka = null;
      this.emitToimipaikkaChange(this.activeToimipaikka);
      return;
    }

    if (this.toimipaikat.length === 1 || (!this.anyToimijaKatselija && this.toimipaikat.length > 0)) {
      this.activeToimipaikka = this.toimipaikat[0];
      this.emitToimipaikkaChange(this.activeToimipaikka);
      return;
    }

    this.toimipaikat = this.toimipaikat.sort((a, b) => {
      return a.nimi.toLowerCase().localeCompare(b.nimi.toLowerCase(), 'fi');
    });

    const previousToimipaikkaOID = localStorage.getItem(VardaCookieEnum.previous_toimipaikka);
    this.activeToimipaikka = this.toimipaikat.find(toimipaikka => toimipaikka.organisaatio_oid === previousToimipaikkaOID) || null;
    this.emitToimipaikkaChange(this.activeToimipaikka);
  }

  openToimipaikka(toimipaikka: VardaToimipaikkaMinimalDto): void {
    this.editToimipaikkaAction = true;
    this.formToimipaikka = toimipaikka;
    this.openToimipaikkaForm(toimipaikka.id);
  }

  toimipaikkaFormValuesChanged(hasChanged: boolean) {
    this.confirmedToimipaikkaFormLeave = !hasChanged;
  }

  openToimipaikkaForm(toimipaikkaId?: number): void {
    this.toimipaikkaData = null;

    if (toimipaikkaId) {
      this.vakajarjestajaApiService.getToimipaikka(toimipaikkaId).subscribe(toimipaikkaData => {
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

      this.vakajarjestajaApiService.getToimipaikat(this.selectedVakajarjestaja.id).subscribe({
        next: toimipaikat => {
          this.vardaVakajarjestajaService.setToimipaikat(toimipaikat);
        },
        error: err => console.error(err)
      });
    }
  }

  setToimipaikka(toimipaikka: VardaToimipaikkaMinimalDto): void {
    if (toimipaikka) {
      localStorage.setItem(VardaCookieEnum.previous_toimipaikka, toimipaikka.organisaatio_oid);
    }
    this.emitToimipaikkaChange(toimipaikka);
  }

  emitToimipaikkaChange(activeToimipaikka?: VardaToimipaikkaMinimalDto): void {
    this.changeToimipaikka.emit({ toimipaikka: activeToimipaikka, toimipaikat: this.toimipaikat });
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }
}
