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
        next: () => {
          this.toimipaikat = this.vardaVakajarjestajaService.getFilteredToimipaikat().katselijaToimipaikat
            .sort((a, b) => a.nimi.toLowerCase().localeCompare(b.nimi.toLowerCase(), 'fi'));
          if (this.toimipaikat.length === 0) {
            this.activeToimipaikka = null;
            this.emitToimipaikkaChange(this.activeToimipaikka);
            return;
          }

          const previousToimipaikkaOid = localStorage.getItem(VardaCookieEnum.previous_toimipaikka);
          this.activeToimipaikka = this.toimipaikat.find(toimipaikka => toimipaikka.organisaatio_oid === previousToimipaikkaOid) || null;

          if (!this.activeToimipaikka && (this.toimipaikat.length === 1 ||
            (!this.anyToimijaKatselija && this.toimipaikat.length > 0))) {
            // Automatically select first toimipaikka if previous toimipaikka was not found and there is only 1 result,
            // or user does not have organization level permissions
            this.activeToimipaikka = this.toimipaikat[0];
            this.emitToimipaikkaChange(this.activeToimipaikka);
          } else {
            this.emitToimipaikkaChange(this.activeToimipaikka);
          }
        },
        error: err => console.error(err)
      })
    );
  }

  openToimipaikka(toimipaikka: VardaToimipaikkaMinimalDto): void {
    this.formToimipaikka = toimipaikka;
    this.toimipaikkaFormOpen = true;
  }

  toimipaikkaFormValuesChanged(hasChanged: boolean) {
    this.confirmedToimipaikkaFormLeave = !hasChanged;
  }

  handleFormClose($eventObject: ModalEvent): void {
    if ($eventObject === ModalEvent.hidden) {
      this.toimipaikkaFormOpen = false;
      this.confirmedToimipaikkaFormLeave = true;
    }
  }

  addToimipaikka(): void {
    this.toimipaikkaFormOpen = true;
    this.formToimipaikka = null;
  }

  updateToimipaikat(toimipaikka: VardaToimipaikkaDTO): void {
    if (toimipaikka?.id) {
      this.vakajarjestajaApiService.getToimipaikat(this.selectedVakajarjestaja.id).subscribe({
        next: result => {
          this.setPreviousToimipaikka(toimipaikka.organisaatio_oid);
          this.vardaVakajarjestajaService.setToimipaikat(result);
        },
        error: err => console.error(err)
      });
    }
  }

  setToimipaikka(toimipaikka: VardaToimipaikkaMinimalDto): void {
    const organisaatioOid = toimipaikka?.organisaatio_oid || null;
    this.setPreviousToimipaikka(organisaatioOid);
    this.emitToimipaikkaChange(toimipaikka);
  }

  setPreviousToimipaikka(organisaatioOid: string) {
    localStorage.setItem(VardaCookieEnum.previous_toimipaikka, organisaatioOid);
  }

  emitToimipaikkaChange(activeToimipaikka?: VardaToimipaikkaMinimalDto): void {
    this.changeToimipaikka.emit({ toimipaikka: activeToimipaikka, toimipaikat: this.toimipaikat });
  }

  closeToimipaikkaForm() {
    this.handleFormClose(ModalEvent.hidden);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }
}
