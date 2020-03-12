import { Component, Input, OnChanges, OnInit, SimpleChange, SimpleChanges } from '@angular/core';
import { HenkilohakuResultDTO } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { TranslateService } from '@ngx-translate/core';
import { VardaHenkiloDTO } from '../../../../utilities/models/dto/varda-henkilo-dto.model';
import { ModalEvent } from '../../../../shared/components/varda-modal-form/varda-modal-form.component';
import { AuthService } from '../../../../core/auth/auth.service';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { VardaKayttooikeusRoles } from '../../../../utilities/varda-kayttooikeus-roles';
import { VardaPageDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-page-dto';
import { VakajarjestajaToimipaikat } from 'projects/virkailija-app/src/app/utilities/models/varda-vakajarjestaja-toimipaikat.model';

class HenkiloHakuResultWithToimipaikka {
  lapsi: HenkilohakuResultDTO;
  toimipaikkaName: string;
  toimipaikka_oid: string;
}

@Component({
  selector: 'app-haku-list',
  templateUrl: './haku-list.component.html',
  styleUrls: ['./haku-list.component.css']
})
export class HakuListComponent implements OnInit, OnChanges {
  @Input() searchResult: VardaPageDto<HenkilohakuResultDTO>;
  resultCount: number;
  searchResultByToimipaikka: Array<HenkiloHakuResultWithToimipaikka>;
  henkiloFormOpen: boolean;
  activeHenkilo: VardaHenkiloDTO;
  toimipaikat: VakajarjestajaToimipaikat;
  userRole: VardaKayttooikeusRoles;
  closeHakuListFormWithoutConfirm: boolean;

  constructor(private translateService: TranslateService,
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService) {
    this.henkiloFormOpen = false;
    this.closeHakuListFormWithoutConfirm = true;
  }

  ngOnInit() {
    this.searchResultByToimipaikka = [];
    this.userRole = this.authService.loggedInUserCurrentKayttooikeus;
  }

  ngOnChanges(changes: SimpleChanges): void {
    const searchResult: SimpleChange = changes.searchResult;
    if (searchResult.currentValue) {
      this.resultCount = searchResult.currentValue.count;
      this.searchResultByToimipaikka = this.flatmapSearchResults(searchResult.currentValue);
    }
  }

  getMaksutietoText(maksutiedot: Array<string>) {
    return maksutiedot.length
      ? 'label.haku-list.maksutieto-found'
      : '';
  }

  flatmapSearchResults(searchResult: VardaPageDto<HenkilohakuResultDTO>): Array<HenkiloHakuResultWithToimipaikka> {
    if (!searchResult) {
      return null;
    }

    const flatMap = (mapFunc, array) =>
      array.reduce((acc, value) =>
        acc.concat(mapFunc(value)), []);
    return flatMap((result: HenkilohakuResultDTO) =>
      [...result.toimipaikat].map(toimipaikka => ({
        toimipaikkaName: this.getToimipaikkaNimiByLang(toimipaikka),
        toimipaikka_oid: toimipaikka.organisaatio_oid,
        lapsi: { ...result },
      })), searchResult.results);
  }

  getToimipaikkaNimiByLang(toimipaikka) {
    return this.translateService.currentLang === 'sv'
      ? toimipaikka.nimi_sv || toimipaikka.nimi
      : toimipaikka.nimi || toimipaikka.nimi_sv;
  }

  hideHenkiloForm($event: ModalEvent) {
    if ($event === ModalEvent.hidden) {
      this.henkiloFormOpen = false;
      this.closeHakuListFormWithoutConfirm = true;
    }
  }

  editHenkilo(result: HenkiloHakuResultWithToimipaikka) {
    this.henkiloFormOpen = true;
    const activeHenkilo = new VardaHenkiloDTO();
    const lapsi = result.lapsi;
    activeHenkilo.id = lapsi.id;
    activeHenkilo.henkilo_oid = lapsi.henkilo.henkilo_oid;
    activeHenkilo.syntyma_pvm = lapsi.henkilo.syntyma_pvm;
    activeHenkilo.url = lapsi.url;
    activeHenkilo.etunimet = lapsi.henkilo.etunimet;
    activeHenkilo.sukunimi = lapsi.henkilo.sukunimi;
    activeHenkilo.lapsi = lapsi.henkilo.lapsi;
    activeHenkilo.tyontekija = lapsi.henkilo.tyontekija;
    this.activeHenkilo = activeHenkilo;
    const toimipaikka = this.vardaVakajarjestajaService.tallentajaToimipaikat.find(toimipaikka => toimipaikka.organisaatio_oid === result.toimipaikka_oid)
    this.vardaVakajarjestajaService.setSelectedToimipaikka(toimipaikka);
  }

  henkiloHakuFormValuesChanged(hasChanged: boolean) {
    this.closeHakuListFormWithoutConfirm = !hasChanged;
  }
}
