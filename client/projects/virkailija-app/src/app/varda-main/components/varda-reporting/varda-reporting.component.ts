import { Component, ElementRef, OnDestroy, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaEntityNames, VardaFieldSet, VardaToimipaikkaDTO, VardaVakajarjestajaUi } from '../../../utilities/models';
import { mergeMap } from 'rxjs/operators';
import { BehaviorSubject, defer, forkJoin, Observable, Subscription } from 'rxjs';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { VardaFormService } from '../../../core/services/varda-form.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaDateService } from '../../services/varda-date.service';
import { VardaPageDto } from '../../../utilities/models/dto/varda-page-dto';
import {
  LapsiByToimipaikkaDTO,
  TyontekijaByToimipaikkaDTO
} from '../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VakajarjestajaToimipaikat } from '../../../utilities/models/varda-vakajarjestaja-toimipaikat.model';
import { BreakpointObserver } from '@angular/cdk/layout';
import * as moment from 'moment';
import { Moment } from 'moment';
import { MatTabChangeEvent } from '@angular/material/tabs';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { MatChipList } from '@angular/material/chips';
import { CodeDTO, KoodistoDTO, VardaKoodistoService } from 'varda-shared';
import { KoodistoEnum } from 'varda-shared';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

enum FilterStringType {
  TRANSLATED_STRING = 'translatedString',
  RAW = 'raw'
}

interface FilterStringParam {
  type: FilterStringType;
  value: string;
  ignoreComma?: boolean;
  lowercase?: boolean;
}

@Component({
  selector: 'app-varda-reporting',
  templateUrl: './varda-reporting.component.html',
  styleUrls: ['./varda-reporting.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class VardaReportingComponent implements OnInit, OnDestroy {
  @ViewChild('lapsiToimipaikkaInput') lapsiToimipaikkaInput: ElementRef<HTMLInputElement>;
  @ViewChild('lapsiToimipaikkaChipList') lapsiToimipaikkaChipList: MatChipList;
  @ViewChild('tyontekijaToimipaikkaInput') tyontekijaToimipaikkaInput: ElementRef<HTMLInputElement>;
  @ViewChild('tyontekijaToimipaikkaChipList') tyontekijaToimipaikkaChipList: MatChipList;

  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  toimipaikat: Array<VardaToimipaikkaDTO>;
  toimipaikanLapset: Array<any>;
  selectedToimipaikanLapsi: any;
  vakajarjestajaToimipaikat: VakajarjestajaToimipaikat;
  userAccess: UserAccess;

  selectedSearchEntity: string = VardaEntityNames.TOIMIPAIKKA;
  nextSearchLink: string;
  prevSearchLink: string;

  lapsiToimipaikat: Array<VardaToimipaikkaMinimalDto>;
  tyontekijaToimipaikat: Array<VardaToimipaikkaMinimalDto>;
  selectedToimipaikat: Array<VardaToimipaikkaMinimalDto> = [];
  toimipaikkaOptions: Array<VardaToimipaikkaMinimalDto> = [];
  filteredToimipaikkaOptions: BehaviorSubject<Array<VardaToimipaikkaMinimalDto>> = new BehaviorSubject([]);
  isNoToimipaikkaResults = false;
  isAllToimipaikatSelected = true;

  toimipaikkaFieldsToBeFormatted: Array<string>;

  toimipaikanLapsetDateFields: Array<string>;
  toimipaikanLapsetBooleanFiels: Array<string>;

  ui: {
    isReportingInitializationError: boolean,
    isResultsEmpty: boolean,
    noOfResults: number
  };

  translatedStringMap = {
    'voimassa': 'label.voimassa',
    'paattynyt': 'label.paattynyt',
    'vakasuhteet': 'label.varhaiskasvatussuhteet',
    'vakapaatokset': 'label.varhaiskasvatuspaatokset',
    'maksutiedot': 'label.maksutiedot',
    'alkanut': 'label.alkanut',
    'palvelussuhteet': 'label.palvelussuhteet',
    'aikavali': 'label.aikavali'
  };

  toimipaikkaSearchValue: string;

  toimipaikkaVoimassaolo = {
    KAIKKI: 'kaikki',
    VOIMASSAOLEVAT: 'voimassa',
    PAATTYNEET: 'paattynyt'
  };

  toimipaikkaFilter: {
    toimintamuoto: string;
    jarjestamismuoto: string;
    voimassaolo: string;
  } = {
    toimintamuoto: '',
    jarjestamismuoto: '',
    voimassaolo: this.toimipaikkaVoimassaolo.KAIKKI
  };

  toimipaikkaFilterString: string;
  isToimipaikkaFiltersAreVisible: boolean;
  isToimipaikkaFilterInactive = true;

  lapsiRajaus = {
    VAKASUHTEET: 'vakasuhteet',
    VAKAPAATOKSET: 'vakapaatokset',
    MAKSUTIEDOT: 'maksutiedot',
    NONE: null
  };

  lapsiSearchValue: string;

  voimassaolo = {
    ALKANUT: 'alkanut',
    PAATTYNYT: 'paattynyt',
    VOIMASSA: 'voimassa',
  };

  lapsiFilter: {
    rajaus: string;
    voimassaolo: string;
    alkamisPvm: Moment;
    paattymisPvm: Moment;
  } = {
      rajaus: this.lapsiRajaus.VAKAPAATOKSET,
      voimassaolo: this.voimassaolo.VOIMASSA,
      alkamisPvm: moment(),
      paattymisPvm: moment()
    };
  isLapsiFilterInactive = false;
  lapsiFilterString: string;
  isLapsiFiltersAreVisible: boolean;

  tyontekijaResults: Array<TyontekijaByToimipaikkaDTO> = null;
  selectedTyontekija: TyontekijaByToimipaikkaDTO = null;

  tyontekijaSearchValue: string;

  tyontekijaRajaus = {
    PALVELUSSUHTEET: 'palvelussuhteet',
    NONE: null
  };

  tyontekijaFilter: {
    rajaus: string;
    voimassaolo: string;
    alkamisPvm: Moment;
    paattymisPvm: Moment;
    tehtavanimike: CodeDTO;
    tutkinto: CodeDTO;
  } = {
    rajaus: this.tyontekijaRajaus.PALVELUSSUHTEET,
    voimassaolo: this.voimassaolo.VOIMASSA,
    alkamisPvm: moment(),
    paattymisPvm: moment(),
    tehtavanimike: null,
    tutkinto: null
  };

  isTyontekijaFilterInactive = false;
  isTyontekijaRajausFilterInactive = false;
  tyontekijaFilterString: string;
  isTyontekijaFiltersAreVisible: boolean;

  tehtavanimikkeet: Array<CodeDTO> = [];
  filteredTehtavanimikeOptions: BehaviorSubject<Array<CodeDTO>> = new BehaviorSubject([]);
  isNoTehtavanimikeResults = false;

  tutkinnot: Array<CodeDTO> = [];
  filteredTutkintoOptions: BehaviorSubject<Array<CodeDTO>> = new BehaviorSubject([]);
  isNoTutkintoResults = false;

  resizeSubscription: Subscription;
  isSmall: boolean;

  constructor(
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaUtilityService: VardaUtilityService,
    private vardaFormService: VardaFormService,
    private translateService: TranslateService,
    private vardaDateService: VardaDateService,
    private breakpointObserver: BreakpointObserver,
    private koodistoService: VardaKoodistoService,
    private authService: AuthService
  ) {
    this.toimipaikat = [];
    this.toimipaikanLapset = null;

    this.ui = {
      isReportingInitializationError: false,
      isResultsEmpty: false,
      noOfResults: null
    };

    this.toimipaikkaFieldsToBeFormatted = [
      'toimintamuoto_koodi',
      'jarjestamismuoto_koodi',
      'kasvatusopillinen_jarjestelma_koodi',
      'toiminnallinenpainotus_kytkin',
      'kielipainotus_kytkin',
      'alkamis_pvm',
      'paattymis_pvm',
      'asiointikieli_koodi',
      'kunta_koodi'
    ];

    this.toimipaikanLapsetDateFields = [
      'vaka_paatos_alkamis_pvm',
      'vaka_paatos_paattymis_pvm',
      'vaka_paatos_hakemus_pvm',
      'vaka_suhde_alkamis_pvm',
      'vaka_suhde_paattymis_pvm'
    ];

    this.toimipaikanLapsetBooleanFiels = [
      'vaka_paatos_vuorohoito_kytkin',
      'vaka_paatos_paivittainen_vaka_kytkin',
      'vaka_paatos_kokopaivainen_vaka_kytkin',
      'vaka_paatos_pikakasittely_kytkin'
    ];

    // For administrative users who can switch between vakajarjestajat
    this.vardaVakajarjestajaService.getSelectedVakajarjestajaObs().subscribe((data) => {
      this.selectedVakajarjestaja = data.vakajarjestaja;
      if (data.onVakajarjestajaChange) {
        if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA) {
          this.searchToimipaikka();
        } else if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
          this.resetToimipaikkaSelect(VardaEntityNames.LAPSI);
          this.filterLapset();
        } else if (this.selectedSearchEntity === VardaEntityNames.TYONTEKIJA) {
          this.resetToimipaikkaSelect(VardaEntityNames.TYONTEKIJA);
          this.filterTyontekijat();
        } else if (this.selectedSearchEntity === VardaEntityNames.YHTEENVETO) {
          // In yhteenveto component
        }
      }
    });

    this.selectedSearchEntity = VardaEntityNames.TOIMIPAIKKA;
    // Hide filters if screen size is small
    this.resizeSubscription = this.breakpointObserver.observe('(min-width: 768px)').subscribe(data => {
      this.isLapsiFiltersAreVisible = this.lapsiFiltersAreFilled() || data.matches;
      this.isToimipaikkaFiltersAreVisible = this.toimipaikkaFiltersAreFilled() || data.matches;
      this.isTyontekijaFiltersAreVisible = this.isTyontekijaFiltersFilled() || data.matches;
      this.isSmall = !data.matches;
    });
  }

  changeSearchEntity($event: MatTabChangeEvent): void {
    this.selectedSearchEntity = $event.tab.ariaLabel;
    this.nextSearchLink = null;
    this.prevSearchLink = null;
    this.lapsiSearchValue = null;
    this.ui.isResultsEmpty = false;
    if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA) {
      this.searchToimipaikka();
    } else if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
      this.resetToimipaikkaSelect(VardaEntityNames.LAPSI);
      this.filterLapset();
    } else if (this.selectedSearchEntity === VardaEntityNames.TYONTEKIJA) {
      this.resetToimipaikkaSelect(VardaEntityNames.TYONTEKIJA);
      this.filterTyontekijat();
    } else if (this.selectedSearchEntity === VardaEntityNames.YHTEENVETO) {
      // In yhteenveto component
    }
  }

  formatForReporting(toimipaikat: Array<VardaToimipaikkaDTO>): Observable<any> {
    const excludedInToimipaikkaReportingFields = [
      'url',
      'hallinnointijarjestelma',
      'vakajarjestaja',
      'toiminnallisetpainotukset_top',
      'kielipainotukset_top',
      'varhaiskasvatussuhteet_top',
      'esiopetussuhteet_top',
      'muutos_pvm',
    ];

    const formattedToimipaikatArr = [];

    return new Observable((toimipaikkaObserver) => {

      if (toimipaikat.length === 0) {
        toimipaikkaObserver.next(formattedToimipaikatArr);
        toimipaikkaObserver.complete();
      }

      return new Observable((painotusObserver) => {
        toimipaikat.forEach((t) => {
          const formattedToimipaikkaObj = { toimipaikka: {}, kielipainotukset: null, toimintapainotukset: null };
          const toimipaikkaKeys = Object.keys(t);
          toimipaikkaKeys.forEach((k) => {
            if (!excludedInToimipaikkaReportingFields.includes(k)) {
              formattedToimipaikkaObj.toimipaikka[k] = t[k];
            }
          });

          if (t.kielipainotus_kytkin || t.toiminnallinenpainotus_kytkin) {
            const toimipaikkaId = this.vardaUtilityService.parseIdFromUrl(t.url);
            forkJoin([
              this.vardaApiWrapperService.getKielipainotuksetByToimipaikka(toimipaikkaId),
              this.vardaApiWrapperService.getToimintapainotuksetByToimipaikka(toimipaikkaId),
            ]).subscribe((painotukset) => {
              formattedToimipaikkaObj.kielipainotukset = painotukset[0];
              formattedToimipaikkaObj.toimintapainotukset = painotukset[1];
              painotusObserver.next(formattedToimipaikkaObj);
            });
            return;
          }

          painotusObserver.next(formattedToimipaikkaObj);
        });
      }).subscribe((d) => {
        formattedToimipaikatArr.push(d);
        if (toimipaikat.length === formattedToimipaikatArr.length) {
          toimipaikkaObserver.next(formattedToimipaikatArr);
          toimipaikkaObserver.complete();
        }
      });
    });
  }

  getDateDisplayValue(value: any): string {
    return this.vardaDateService.getDateDisplayValue(value);
  }

  getToimipaikatForReporting(searchParams: any, nextLink: string): Observable<any> {
    return this.vardaApiWrapperService.getToimipaikatForVakajarjestaja(
      this.vardaVakajarjestajaService.selectedVakajarjestaja.id, searchParams, nextLink);
  }

  getToimipaikanLapsetForReporting(searchParams: any, nextLink: string): Observable<VardaPageDto<LapsiByToimipaikkaDTO>> {
    return this.vardaApiWrapperService.getLapsetForToimipaikat(searchParams, nextLink);
  }

  getVakajarjestajaId() {
    return this.vardaVakajarjestajaService.selectedVakajarjestaja.id;
  }

  getVakajarjestajaName(toimipaikkaObj): string {
    const vakajarjestajaNimi = this.vardaVakajarjestajaService.selectedVakajarjestaja.nimi;
    const toimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().allToimipaikat;
    const foundToimipaikka = toimipaikat.find(toimipaikka => toimipaikka.id === toimipaikkaObj.id);
    return foundToimipaikka?.paos_organisaatio_nimi || vakajarjestajaNimi;
  }

  searchToimipaikka(): any {
    const searchParams = {};

    this.isToimipaikkaFilterInactive = !this.toimipaikkaFiltersAreFilled();
    this.updateToimipaikkaFilterString();

    if (this.toimipaikkaSearchValue) {
      searchParams['nimi'] = this.toimipaikkaSearchValue;
    }
    if (this.toimipaikkaFilter.voimassaolo !== this.toimipaikkaVoimassaolo.KAIKKI) {
      searchParams['voimassaolo'] = this.toimipaikkaFilter.voimassaolo;
    }
    if (this.toimipaikkaFilter.jarjestamismuoto !== '') {
      searchParams['jarjestamismuoto_koodi'] = this.toimipaikkaFilter.jarjestamismuoto.toLowerCase();
    }
    if (this.toimipaikkaFilter.toimintamuoto !== '') {
      searchParams['toimintamuoto_koodi'] = this.toimipaikkaFilter.toimintamuoto.toLowerCase();
    }

    this.getToimipaikatForReporting(searchParams, null).subscribe(this.updateToimipaikat.bind(this));
  }

  searchLapsi(): void {
    const searchParams = {};

    const searchVal = this.lapsiSearchValue;
    searchParams['search'] = searchVal ? searchVal : '';

    if (this.lapsiFiltersAreFilled()) {
      searchParams['rajaus'] = this.lapsiFilter.rajaus;
      searchParams['voimassaolo'] = this.lapsiFilter.voimassaolo;
      searchParams['alkamis_pvm'] = this.vardaDateService.momentToVardaDate(this.lapsiFilter.alkamisPvm);
      searchParams['paattymis_pvm'] = this.vardaDateService.momentToVardaDate(this.lapsiFilter.paattymisPvm);
    }

    if (!this.isAllToimipaikatSelected) {
      searchParams['toimipaikat'] = this.selectedToimipaikat.map(toimipaikka => toimipaikka.id).join(',');
    }

    if (!this.isAllToimipaikatSelected && this.selectedToimipaikat.length === 0) {
      this.ui.isResultsEmpty = true;
      return;
    }

    this.selectedToimipaikanLapsi = null;
    this.toimipaikanLapset = null;
    this.getToimipaikanLapsetForReporting(searchParams, null).subscribe({
      next: this.updateToimipaikanLapset.bind(this),
      error: (err) => this.updateToimipaikanLapset({ results: [], count: 0 })
    });
  }

  searchMore(less: Boolean = false): any {
    const searchLink = less ? this.prevSearchLink : this.nextSearchLink;
    if (searchLink) {
      if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA) {
        this.getToimipaikatForReporting(null, searchLink).subscribe(this.updateToimipaikat.bind(this));
      } else if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
        this.getToimipaikanLapsetForReporting(null, searchLink).subscribe(this.updateToimipaikanLapset.bind(this));
      } if (this.selectedSearchEntity === VardaEntityNames.TYONTEKIJA) {
        this.getTyontekijatForReporting(null, searchLink).subscribe(this.updateTyontekijaResults.bind(this));
      }
    }
  }

  updateToimipaikanLapset(lapsetResp: any): void {
    this.ui.isResultsEmpty = false;

    if (lapsetResp) {
      this.toimipaikanLapset = lapsetResp.results;

      this.toimipaikanLapset.forEach(lapsi => {
        delete lapsi.lapsi_url;
      });
    }

    this.nextSearchLink = lapsetResp.next;
    this.prevSearchLink = lapsetResp.previous;
    this.ui.noOfResults = lapsetResp.count;

    if (this.selectedSearchEntity === VardaEntityNames.LAPSI && this.toimipaikanLapset.length === 0) {
      this.ui.isResultsEmpty = true;
    }
  }

  updateToimipaikat(toimipaikatResp: any): void {
    const concatArr = !!toimipaikatResp.previous;
    this.ui.isResultsEmpty = false;
    this.nextSearchLink = toimipaikatResp.next;

    this.formatForReporting(toimipaikatResp.results).subscribe((formattedToimipaikatArr) => {
      if (concatArr) {
        this.toimipaikat = this.toimipaikat.concat(formattedToimipaikatArr);
      } else {
        this.toimipaikat = formattedToimipaikatArr;
      }
      this.toimipaikat = this.toimipaikat.sort((a, b) => {
        return a.toimipaikka.nimi.toLowerCase().localeCompare(b.toimipaikka.nimi.toLowerCase(), 'fi');
      });

      if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA && this.toimipaikat.length === 0) {
        this.ui.isResultsEmpty = true;
      } else {
        this.ui.noOfResults = toimipaikatResp.count;
      }
    });
  }

  showLapsi(lapsiId: number) {
    // unselect if lapsi was already selected
    if (this.selectedToimipaikanLapsi && this.selectedToimipaikanLapsi.lapsi_id === lapsiId) {
      this.selectedToimipaikanLapsi = null;
    } else {
      this.selectedToimipaikanLapsi = this.toimipaikanLapset.filter(lapsi => lapsi.lapsi_id === lapsiId)[0];
    }
  }

  getVakaJarjestajaText(lapsi: LapsiByToimipaikkaDTO): string {
    return lapsi.paos_organisaatio_nimi;
  }

  fillLapsiFilter() {
    this.lapsiFilter.voimassaolo = this.voimassaolo.VOIMASSA;
    this.lapsiFilter.alkamisPvm = moment();
    this.lapsiFilter.paattymisPvm = moment();
  }

  filterLapset() {
    if (this.selectedSearchEntity !== VardaEntityNames.LAPSI) {
      return;
    }

    if (this.isLapsiFilterInactive) {
      this.isLapsiFilterInactive = false;
      this.fillLapsiFilter();
    }

    if (this.lapsiFilter.rajaus === this.lapsiRajaus.NONE) {
      this.isLapsiFilterInactive = true;
      this.clearLapsiFilter();
      return;
    }

    if (!this.lapsiFiltersAreFilled()) {
      return;
    }

    this.updateLapsiFilterString();
    this.searchLapsi();
  }

  updateLapsiFilterString() {
    this.lapsiFilterString = '';
    const stringParams: Array<FilterStringParam> = [];

    stringParams.push({value: this.lapsiFilter.rajaus, type: FilterStringType.TRANSLATED_STRING});
    stringParams.push({value: this.lapsiFilter.voimassaolo, type: FilterStringType.TRANSLATED_STRING, lowercase: true});
    stringParams.push({value: 'aikavali', type: FilterStringType.TRANSLATED_STRING, lowercase: true});
    stringParams.push({
      value: `${this.lapsiFilter.alkamisPvm.format(VardaDateService.vardaDefaultDateFormat)} -
        ${this.lapsiFilter.paattymisPvm.format(VardaDateService.vardaDefaultDateFormat)}`,
      type: FilterStringType.RAW,
      ignoreComma: true
    });

    this.lapsiFilterString = this.getFilterString(stringParams);
  }

  clearLapsiFilter() {
    this.lapsiFilter.rajaus = this.lapsiRajaus.NONE;
    this.lapsiFilter.voimassaolo = null;
    this.lapsiFilter.alkamisPvm = null;
    this.lapsiFilter.paattymisPvm = null;
    this.isLapsiFilterInactive = true;
    this.searchLapsi();
  }

  lapsiFiltersAreFilled(): boolean {
    return this.lapsiFilter.rajaus !== this.lapsiRajaus.NONE && this.lapsiFilter.rajaus !== null &&
      this.lapsiFilter.voimassaolo !== null && this.lapsiFilter.alkamisPvm !== null &&
      this.lapsiFilter.paattymisPvm !== null;
  }

  toimipaikkaAutocompleteSelected(event: MatAutocompleteSelectedEvent) {
    const selectedToimipaikka = event.option.value;

    if (selectedToimipaikka) {
      this.isAllToimipaikatSelected = false;
      this.selectedToimipaikat.push(selectedToimipaikka);

      // Remove selected option from Autocomplete
      this.filteredToimipaikkaOptions.next(this.toimipaikkaOptions.filter(toimipaikka => {
        return toimipaikka.id !== selectedToimipaikka.id && this.selectedToimipaikat.indexOf(toimipaikka) === -1;
      }));
    } else {
      // All toimipaikat selection is applied
      this.isAllToimipaikatSelected = true;
      this.selectedToimipaikat = [];
      this.filteredToimipaikkaOptions.next([...this.toimipaikkaOptions]);
    }

    if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
      this.lapsiToimipaikkaInput.nativeElement.value = '';
      setTimeout(() => {
        this.lapsiToimipaikkaChipList.chips.last.focus();
      });
    } else if (this.selectedSearchEntity === VardaEntityNames.TYONTEKIJA) {
      this.tyontekijaToimipaikkaInput.nativeElement.value = '';
      setTimeout(() => {
        this.tyontekijaToimipaikkaChipList.chips.last.focus();
      });
    }
    this.isNoToimipaikkaResults = false;
  }

  removeSelectedToimipaikka(removedToimipaikka: VardaToimipaikkaMinimalDto) {
    if (removedToimipaikka) {
      this.selectedToimipaikat.splice(this.selectedToimipaikat.indexOf(removedToimipaikka), 1);

      // Add removed option back to Autocomplete
      this.filteredToimipaikkaOptions.next(this.toimipaikkaOptions.filter(toimipaikka => {
        return this.selectedToimipaikat.indexOf(toimipaikka) === -1;
      }));
    } else {
      // Reset input if all toimipaikat selection is cleared
      this.isAllToimipaikatSelected = false;
      this.filteredToimipaikkaOptions.next([...this.toimipaikkaOptions]);
    }

    if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
      this.lapsiToimipaikkaInput.nativeElement.value = '';
    } else if (this.selectedSearchEntity === VardaEntityNames.TYONTEKIJA) {
      this.tyontekijaToimipaikkaInput.nativeElement.value = '';
    }

    this.isNoToimipaikkaResults = false;
  }

  toimipaikkaSelectInputChange(event: Event) {
    const targetValue = (<HTMLInputElement> event.target).value;
    const results = this.toimipaikkaOptions.filter(toimipaikka => {
      return toimipaikka.nimi.toLowerCase().includes(targetValue.toLowerCase()) && this.selectedToimipaikat.indexOf(toimipaikka) === -1;
    });

    if (results.length === 0) {
      this.isNoToimipaikkaResults = true;
      this.filteredToimipaikkaOptions.next([]);
    } else {
      this.isNoToimipaikkaResults = false;
      this.filteredToimipaikkaOptions.next(results);
    }
  }

  clearToimipaikkaFilter() {
    this.toimipaikkaFilter.voimassaolo = this.toimipaikkaVoimassaolo.KAIKKI;
    this.toimipaikkaFilter.toimintamuoto = '';
    this.toimipaikkaFilter.jarjestamismuoto = '';
    this.isToimipaikkaFilterInactive = true;
    this.searchToimipaikka();
  }

  toimipaikkaFiltersAreFilled(): boolean {
    return this.toimipaikkaFilter.voimassaolo !== this.toimipaikkaVoimassaolo.KAIKKI ||
      this.toimipaikkaFilter.jarjestamismuoto !== '' || this.toimipaikkaFilter.toimintamuoto !== '';
  }

  updateToimipaikkaFilterString() {
    this.toimipaikkaFilterString = '';
    const stringParams: Array<FilterStringParam> = [];

    if (this.toimipaikkaFilter.voimassaolo !== this.toimipaikkaVoimassaolo.KAIKKI) {
      stringParams.push({value: this.toimipaikkaFilter.voimassaolo, type: FilterStringType.TRANSLATED_STRING});
    }

    stringParams.push({value: this.toimipaikkaFilter.toimintamuoto, type: FilterStringType.RAW});
    stringParams.push({value: this.toimipaikkaFilter.jarjestamismuoto, type: FilterStringType.RAW});

    this.toimipaikkaFilterString = this.getFilterString(stringParams);
  }

  getToimipaikkaKeys(toimipaikka: VardaToimipaikkaDTO): Array<string> {
    return Object.keys(toimipaikka.toimipaikka);
  }

  searchTyontekija(): void {
    const searchParams = {};

    this.isTyontekijaFilterInactive = !this.isTyontekijaFiltersFilled();

    searchParams['search'] = this.tyontekijaSearchValue ? this.tyontekijaSearchValue : '';

    if (this.isTyontekijaRajausFiltersFilled()) {
      searchParams['rajaus'] = this.tyontekijaFilter.rajaus;
      searchParams['voimassaolo'] = this.tyontekijaFilter.voimassaolo;
      searchParams['alkamis_pvm'] = this.vardaDateService.momentToVardaDate(this.tyontekijaFilter.alkamisPvm);
      searchParams['paattymis_pvm'] = this.vardaDateService.momentToVardaDate(this.tyontekijaFilter.paattymisPvm);
    }
    if (this.tyontekijaFilter.tehtavanimike !== null) {
      searchParams['tehtavanimike'] = this.tyontekijaFilter.tehtavanimike.code_value;
    }
    if (this.tyontekijaFilter.tutkinto !== null) {
      searchParams['tutkinto'] = this.tyontekijaFilter.tutkinto.code_value;
    }

    if (!this.isAllToimipaikatSelected && this.selectedToimipaikat.length === 0) {
      this.ui.isResultsEmpty = true;
      return;
    }

    if (!this.isAllToimipaikatSelected) {
      searchParams['toimipaikat'] = this.selectedToimipaikat.map(toimipaikka => toimipaikka.id).join(',');
    }

    this.selectedTyontekija = null;
    this.tyontekijaResults = null;
    this.getTyontekijatForReporting(searchParams, null).subscribe({
      next: this.updateTyontekijaResults.bind(this),
      error: () => this.updateTyontekijaResults({ results: [], count: 0 })
    });
  }

  filterTyontekijat(): void {
    if (this.selectedSearchEntity !== VardaEntityNames.TYONTEKIJA) {
      return;
    }

    if (this.isTyontekijaRajausFilterInactive) {
      this.isTyontekijaRajausFilterInactive = false;
      this.fillTyontekijaRajausFilter();
    }

    if (this.tyontekijaFilter.rajaus === this.tyontekijaRajaus.NONE) {
      this.isTyontekijaRajausFilterInactive = true;
      this.clearTyontekijaRajausFilter();
      return;
    }

    if (!this.isTyontekijaFiltersFilled()) {
      return;
    }

    this.updateTyontekijaFilterString();
    this.searchTyontekija();
  }

  fillTyontekijaRajausFilter() {
    this.tyontekijaFilter.voimassaolo = this.voimassaolo.VOIMASSA;
    this.tyontekijaFilter.alkamisPvm = moment();
    this.tyontekijaFilter.paattymisPvm = moment();
  }

  clearTyontekijaRajausFilter() {
    this.tyontekijaFilter.rajaus = this.tyontekijaRajaus.NONE;
    this.tyontekijaFilter.voimassaolo = null;
    this.tyontekijaFilter.alkamisPvm = null;
    this.tyontekijaFilter.paattymisPvm = null;
    this.isTyontekijaRajausFilterInactive = true;
    this.updateTyontekijaFilterString();
    this.searchTyontekija();
  }

  clearTyontekijaFilter() {
    this.tyontekijaFilter.tehtavanimike = null;
    this.tyontekijaFilter.tutkinto = null;
    this.isTyontekijaFilterInactive = true;
    this.clearTyontekijaRajausFilter();
  }

  isTyontekijaFiltersFilled(): boolean {
    return this.isTyontekijaRajausFiltersFilled() || (this.tyontekijaFilter.rajaus === this.tyontekijaRajaus.NONE &&
      (this.tyontekijaFilter.tehtavanimike !== null || this.tyontekijaFilter.tutkinto !== null));
  }

  isTyontekijaRajausFiltersFilled(): boolean {
    return this.tyontekijaFilter.rajaus !== this.tyontekijaRajaus.NONE &&
      this.tyontekijaFilter.voimassaolo !== null && this.tyontekijaFilter.alkamisPvm !== null &&
      this.tyontekijaFilter.paattymisPvm !== null;
  }

  updateTyontekijaFilterString() {
    this.tyontekijaFilterString = '';
    const stringParams: Array<FilterStringParam> = [];

    if (this.isTyontekijaRajausFiltersFilled()) {
      stringParams.push({value: this.tyontekijaFilter.rajaus, type: FilterStringType.TRANSLATED_STRING});
      stringParams.push({value: this.tyontekijaFilter.voimassaolo, type: FilterStringType.TRANSLATED_STRING, lowercase: true});
      stringParams.push({value: 'aikavali', type: FilterStringType.TRANSLATED_STRING, lowercase: true});
      stringParams.push({
        value: `${this.tyontekijaFilter.alkamisPvm.format(VardaDateService.vardaDefaultDateFormat)} -
        ${this.tyontekijaFilter.paattymisPvm.format(VardaDateService.vardaDefaultDateFormat)}`,
        type: FilterStringType.RAW,
        ignoreComma: true
      });
    }

    stringParams.push({value: this.tyontekijaFilter.tehtavanimike?.code_value, type: FilterStringType.RAW});
    stringParams.push({value: this.tyontekijaFilter.tutkinto?.code_value, type: FilterStringType.RAW});

    this.tyontekijaFilterString = this.getFilterString(stringParams);
  }

  getFilterString(params: Array<FilterStringParam>): string {
    let resultString = '';

    params.forEach((param, index) => {
      if (!param.value) {
        return;
      }

      if (resultString !== '') {
        resultString += param.ignoreComma ? ' ' : ', ';
      }

      let newValue;
      switch (param.type) {
        case FilterStringType.TRANSLATED_STRING:
          newValue = this.translateService.instant(this.translatedStringMap[param.value]);
          break;
        case FilterStringType.RAW:
        default:
          newValue = param.value;
      }

      resultString += param.lowercase ? newValue.toLowerCase() : newValue;
    });

    return resultString;
  }

  tehtavanimikeOnChange(tehtavanimike: CodeDTO) {
    this.filterTyontekijat();
  }

  tutkintoOnChange(tutkinto: CodeDTO) {
    this.filterTyontekijat();
  }

  getTyontekijatForReporting(searchParams: any, nextLink: string): Observable<VardaPageDto<TyontekijaByToimipaikkaDTO>> {
    return this.vardaApiWrapperService.getTyontekijatForToimipaikat(searchParams, nextLink);
  }

  updateTyontekijaResults(tyontekijatResponse: VardaPageDto<TyontekijaByToimipaikkaDTO>): void {
    this.ui.isResultsEmpty = false;

    if (tyontekijatResponse) {
      this.tyontekijaResults = tyontekijatResponse.results;

      this.tyontekijaResults.forEach(tyontekija => {
        delete tyontekija.tyontekija_url;
      });
    }

    this.nextSearchLink = tyontekijatResponse.next;
    this.prevSearchLink = tyontekijatResponse.previous;
    this.ui.noOfResults = tyontekijatResponse.count;

    if (this.selectedSearchEntity === VardaEntityNames.TYONTEKIJA && this.tyontekijaResults.length === 0) {
      this.ui.isResultsEmpty = true;
    }
  }

  showTyontekija(tyontekija: TyontekijaByToimipaikkaDTO) {
    // Unselect if tyontekija was already selected
    if (this.selectedTyontekija && this.selectedTyontekija === tyontekija) {
      this.selectedTyontekija = null;
    } else {
      this.selectedTyontekija = tyontekija;
    }
  }

  getKoodistoFromKoodistoService(name: KoodistoEnum) {
    return this.koodistoService.getKoodisto(name);
  }

  getCodeFromKoodistoService(koodistoName: KoodistoEnum, code: string) {
    return this.koodistoService.getCodeValueFromKoodisto(koodistoName, code);
  }

  resetToimipaikkaSelect(entity: string) {
    this.selectedToimipaikat = [];
    this.isAllToimipaikatSelected = true;
    this.isNoToimipaikkaResults = false;
    if (entity === VardaEntityNames.LAPSI) {
      this.toimipaikkaOptions = this.lapsiToimipaikat;
    } else if (entity === VardaEntityNames.TYONTEKIJA) {
      this.toimipaikkaOptions = this.tyontekijaToimipaikat;
    } else {
      this.toimipaikkaOptions = [];
    }
    this.filteredToimipaikkaOptions.next([...this.toimipaikkaOptions]);
  }

  getCodeUiString(code: CodeDTO): string {
    return `${code.name} (${code.code_value})`;
  }

  ngOnInit() {
    this.vakajarjestajaToimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat();
    this.userAccess = this.authService.getUserAccessIfAnyToimipaikka(this.vakajarjestajaToimipaikat.katselijaToimipaikat);
    const toimipaikatByPermissions = this.authService.getToimipaikatByLapsiTyontekijaPermissions(this.vakajarjestajaToimipaikat.katselijaToimipaikat);
    this.lapsiToimipaikat = toimipaikatByPermissions.lapsiToimipaikat;
    this.tyontekijaToimipaikat = toimipaikatByPermissions.tyontekijaToimipaikat;
    if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
      this.resetToimipaikkaSelect(VardaEntityNames.LAPSI);
    } else if (this.selectedSearchEntity === VardaEntityNames.TYONTEKIJA) {
      this.resetToimipaikkaSelect(VardaEntityNames.TYONTEKIJA);
    }
    forkJoin([
      this.getKoodistoFromKoodistoService(this.koodistoEnum.tehtavanimike),
      this.getKoodistoFromKoodistoService(this.koodistoEnum.tutkinto)
    ]).pipe(mergeMap((data) => {
      this.tehtavanimikkeet = (<KoodistoDTO> data[0]).codes;
      this.filteredTehtavanimikeOptions.next(this.tehtavanimikkeet);
      this.tutkinnot = (<KoodistoDTO> data[1]).codes;
      this.filteredTutkintoOptions.next(this.tutkinnot);
      return this.getToimipaikatForReporting(null, null);
    })).subscribe({
      next: this.updateToimipaikat.bind(this),
      error: () => {
        this.ui.isReportingInitializationError = true;
      },
    });

    this.filterLapset();
    this.filterTyontekijat();
  }

  ngOnDestroy(): void {
    this.resizeSubscription.unsubscribe();
  }
}
