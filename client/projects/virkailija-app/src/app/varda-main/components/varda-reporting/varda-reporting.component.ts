import { Component, OnDestroy, OnInit } from '@angular/core';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaEntityNames, VardaFieldSet, VardaToimipaikkaDTO, VardaWidgetNames } from '../../../utilities/models';
import { mergeMap } from 'rxjs/operators';
import { forkJoin, Observable, Subscription } from 'rxjs';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { VardaFormService } from '../../../core/services/varda-form.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaDateService } from '../../services/varda-date.service';
import { VardaKielikoodistoService } from '../../../core/services/varda-kielikoodisto.service';
import { VardaKuntakoodistoService } from '../../../core/services/varda-kuntakoodisto.service';
import { VardaPageDto } from '../../../utilities/models/dto/varda-page-dto';
import { LapsiByToimipaikkaDTO } from '../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VakajarjestajaToimipaikat } from '../../../utilities/models/varda-vakajarjestaja-toimipaikat.model';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Moment } from 'moment';
import * as moment from 'moment';

@Component({
  selector: 'app-varda-reporting',
  templateUrl: './varda-reporting.component.html',
  styleUrls: ['./varda-reporting.component.css']
})
export class VardaReportingComponent implements OnInit, OnDestroy {

  toimipaikat: Array<VardaToimipaikkaDTO>;
  toimipaikanLapset: Array<any>;
  selectedToimipaikanLapsi: any;
  vakajarjestajaToimipaikat: VakajarjestajaToimipaikat;

  toimipaikatFieldSets: Array<VardaFieldSet>;
  toimintapainotuksetFieldSets: Array<VardaFieldSet>;
  varhaiskasvatuspaatoksetFieldSets: Array<VardaFieldSet>;

  toimipaikkaSearchValue: string;
  lapsiSearchValue: string;
  selectedSearchEntity: string = VardaEntityNames.TOIMIPAIKKA;
  nextSearchLink: string;
  prevSearchLink: string;
  toimipaikanLapsetSelectedToimipaikka: VardaToimipaikkaDTO;

  toimipaikkaFieldsToBeFormatted: Array<string>;

  toimipaikanLapsetDateFields: Array<string>;
  toimipaikanLapsetBooleanFiels: Array<string>;

  ui: {
    reportingInitializationError: boolean,
    resultsEmpty: boolean,
    noOfResults: number
  };

  labelYes: string;
  labelNo: string;

  lapsiRajaus = {
    VAKASUHTEET: 'vakasuhteet',
    VAKAPAATOKSET: 'vakapaatokset',
    MAKSUTIEDOT: 'maksutiedot',
    NONE: null
  };

  lapsiVoimassaolo = {
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
      voimassaolo: this.lapsiVoimassaolo.VOIMASSA,
      alkamisPvm: moment(),
      paattymisPvm: moment()
    };
  lapsiFilterInactive = false;
  lapsiFilterString: string;
  lapsiFiltersAreVisible: boolean;

  resizeSubscription: Subscription;
  isSmall: boolean;

  constructor(
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private vardaUtilityService: VardaUtilityService,
    private vardaFormService: VardaFormService,
    private translateService: TranslateService,
    private vardaDateService: VardaDateService,
    private vardaKielikoodistoService: VardaKielikoodistoService,
    private vardaKuntakoodistoService: VardaKuntakoodistoService,
    private breakpointObserver: BreakpointObserver
  ) {
    this.toimipaikat = [];
    this.toimipaikanLapset = null;

    this.ui = {
      reportingInitializationError: false,
      resultsEmpty: false,
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

    this.translateService.onLangChange.subscribe(() => {
      this.updateLabelTranslations();
    });
    this.updateLabelTranslations();

    // For administrative users who can switch between toimipaikkas
    this.vardaVakajarjestajaService.getSelectedVakajarjestajaObs().subscribe((data) => {
      if (data.onVakajarjestajaChange) {
        if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA) {
          this.searchToimipaikka();
        } else if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
          this.searchLapsi();
        } else if (this.selectedSearchEntity === VardaEntityNames.YHTEENVETO) {
          // In yhteenveto component
        }
      }
    });

    this.selectedSearchEntity = VardaEntityNames.TOIMIPAIKKA;
    // Hide filters if screen size is small
    this.resizeSubscription = this.breakpointObserver.observe('(min-width: 768px)').subscribe(data => {
      this.lapsiFiltersAreVisible = this.lapsiFiltersAreFilled() || data.matches;
      this.isSmall = !data.matches;
    });
  }

  changeSearchEntity($event): any {
    this.selectedSearchEntity = $event.value;
    this.nextSearchLink = null;
    this.prevSearchLink = null;
    this.lapsiSearchValue = null;
    this.ui.resultsEmpty = false;
    if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA) {
      this.searchToimipaikka();
    } else if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
      this.searchLapsi();
    } else if (this.selectedSearchEntity === VardaEntityNames.YHTEENVETO) {
      // In yhteenveto component
    }
  }

  formatToimipaikkaDisplayValue(key: string, val: any): string {
    let rv = val;
    let fieldSets, fieldsToBeFormatted;

    if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA) {
      fieldSets = this.toimipaikatFieldSets;
      fieldsToBeFormatted = this.toimipaikkaFieldsToBeFormatted;
    }

    if (fieldsToBeFormatted.includes(key)) {
      const field = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey(key, fieldSets);

      if (field && (field.widget === VardaWidgetNames.SELECT || field.widget === VardaWidgetNames.SELECTARR)) {

        if (!field.koodisto) {
          const selectedOption = field.options.find((opt) => opt.code === val);
          rv = this.getOptionDisplayName(selectedOption);
        }

        if (field.koodisto === 'kielikoodisto') {
          rv = this.getKielikoodiDisplayValue(val);
        }

        if (field.koodisto === 'kuntakoodisto') {
          rv = this.getKuntakoodiDisplayValue(val);
        }
      }

      if (field && field.widget === VardaWidgetNames.CHECKBOXGROUP) {
        const selectedOptions = [];
        val.forEach((chkValue) => {
          const selectedOption = field.options.find((opt) => opt.code === chkValue);
          const displayValue = this.getOptionDisplayName(selectedOption);
          selectedOptions.push(displayValue);
        });
        rv = selectedOptions;
      }

      if (key === 'kielipainotus_kytkin' || key === 'toiminnallinenpainotus_kytkin') {
        rv = val ? this.labelYes : this.labelNo;
      }

      if (field && field.widget === VardaWidgetNames.DATE) {
        rv = this.vardaDateService.vardaDateToUIStrDate(val);
      }
    }

    return rv || key === 'varhaiskasvatuspaikat' ? rv : '-';
  }

  formatForReporting(toimipaikat: Array<VardaToimipaikkaDTO>): Observable<any> {
    const excludedInToimipaikkaReportingFields = [
      'url',
      'lahdejarjestelma',
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

  getKielikoodiDisplayValue(val: Array<string>): string {
    try {
      let rv = '';
      const kielikoodiValues = val.map((kieliKoodi) => {
        const selectedOption = this.vardaKielikoodistoService.getKielikoodistoOptionByLangAbbreviation(kieliKoodi);
        const kielikoodiMetadata = this.vardaKielikoodistoService.getKielikoodistoOptionMetadataByLang(selectedOption.metadata,
          this.translateService.currentLang);
        rv = kielikoodiMetadata.nimi;
        return rv ? rv : null;
      });
      return kielikoodiValues ? kielikoodiValues.join(', ') : null;
    } catch (e) {
      console.log(e);
      return '-';
    }
  }

  getKielikoodiDisplayValueByString(val: string): string {
    try {
      let rv: string;
      const selectedOption = this.vardaKielikoodistoService.getKielikoodistoOptionByLangAbbreviation(val);
      const kielikoodiMetadata = this.vardaKielikoodistoService.getKielikoodistoOptionMetadataByLang(selectedOption.metadata,
        this.translateService.currentLang);
      rv = kielikoodiMetadata.nimi;
      return rv ? rv : null;
    } catch (e) {
      console.log(e);
      return '-';
    }
  }

  getKuntakoodiDisplayValue(val: string): string {
    try {
      let rv: string;
      const selectedOption = this.vardaKuntakoodistoService.getKuntakoodistoOptionByKuntakoodi(val);
      const kuntakoodiMetadata = this.vardaKuntakoodistoService.getKuntaKoodistoOptionMetadataByLang(selectedOption.metadata,
        this.translateService.currentLang);
      rv = kuntakoodiMetadata.nimi;
      return rv;
    } catch (e) {
      return '-';
    }
  }

  showLapsiRow(key: string, val: any): boolean {
    if (key === 'vaka_paatos_paivittainen_vaka_kytkin' || key === 'vaka_paatos_kokopaivainen_vaka_kytkin') {
      const vuorohoitoKytkinVal = val['vaka_paatos_vuorohoito_kytkin'];
      if (vuorohoitoKytkinVal) {
        return false;
      }
    }
    return true;
  }

  getDateDisplayValue(value: any): string {
    const rv = this.vardaDateService.vardaDateToUIStrDate(value);
    return rv ? rv : '-';
  }

  getToimintapainotusDisplayValue(val: string): string {
    try {
      let rv = '';
      const field = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey('toimintapainotus_koodi',
        this.toimintapainotuksetFieldSets);
      if (field) {
        const selectedOption = field.options.find((opt) => opt.code === val);
        rv = this.getOptionDisplayName(selectedOption);
      }
      return rv;
    } catch (e) {
      return '-';
    }
  }

  getOptionDisplayName(option: any): string {
    try {
      let rv = '';
      const lang = this.translateService.currentLang.toUpperCase();
      const prop = (lang === 'SV') ? 'displayNameSv' : 'displayNameFi';

      if (option.displayName && option.displayName[prop]) {
        rv = option.displayName[prop];
      }
      return rv;
    } catch (e) {
      return '-';
    }
  }

  getSearchInputLabel(): string {
    let rv = '';
    if (this.selectedSearchEntity === VardaEntityNames.TOIMIPAIKKA) {
      rv = 'label.toimipaikannimi';
    } else if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
      rv = 'label.toimipaikka';
    }

    return rv;
  }

  getToimipaikatForReporting(searchParams: any, nextLink: string): Observable<any> {
    return this.vardaApiWrapperService.getToimipaikatForVakajarjestaja(
      this.vardaVakajarjestajaService.selectedVakajarjestaja.id, searchParams, nextLink);
  }

  getToimipaikanLapsetForReporting(searchParams: any, nextLink: string): Observable<VardaPageDto<LapsiByToimipaikkaDTO>> {
    const selectedToimipaikkaId = this.vardaUtilityService.parseIdFromUrl(this.toimipaikanLapsetSelectedToimipaikka.url);
    return this.vardaApiWrapperService.getLapsetForToimipaikka(selectedToimipaikkaId, searchParams, nextLink);
  }

  getToimipaikkaId() {
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

    if (this.toimipaikkaSearchValue) {
      searchParams['nimi'] = this.toimipaikkaSearchValue;
    }

    this.getToimipaikatForReporting(searchParams, null).subscribe(this.updateToimipaikat.bind(this));
  }

  searchLapsi(): any {
    const searchParams = {};

    const searchVal = this.lapsiSearchValue;
    searchParams['search'] = searchVal ? searchVal : '';

    if (this.lapsiFiltersAreFilled()) {
      searchParams['rajaus'] = this.lapsiFilter.rajaus;
      searchParams['voimassaolo'] = this.lapsiFilter.voimassaolo;
      searchParams['alkamis_pvm'] = this.vardaDateService.momentToVardaDate(this.lapsiFilter.alkamisPvm);
      searchParams['paattymis_pvm'] = this.vardaDateService.momentToVardaDate(this.lapsiFilter.paattymisPvm);
    }

    if (!this.toimipaikanLapsetSelectedToimipaikka) {
      this.ui.resultsEmpty = true;
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
        this.getToimipaikatForReporting(null, searchLink).subscribe((this.updateToimipaikat.bind(this)));
      } else if (this.selectedSearchEntity === VardaEntityNames.LAPSI) {
        this.getToimipaikanLapsetForReporting(null, searchLink).subscribe((this.updateToimipaikanLapset.bind(this)));
      }
    }
  }

  updateToimipaikanLapset(lapsetResp: any): void {
    this.ui.resultsEmpty = false;

    if (lapsetResp) {
      this.toimipaikanLapset = lapsetResp.results;

      this.toimipaikanLapset.forEach(function (v) {
        delete v.lapsi_url;
      });
    }

    this.nextSearchLink = lapsetResp.next;
    this.prevSearchLink = lapsetResp.previous;
    this.ui.noOfResults = lapsetResp.count;

    if (this.selectedSearchEntity === VardaEntityNames.LAPSI && this.toimipaikanLapset.length === 0) {
      this.ui.resultsEmpty = true;
    }
  }

  updateToimipaikat(toimipaikatResp: any): void {
    const concatArr = !!toimipaikatResp.previous;
    this.ui.resultsEmpty = false;
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
        this.ui.resultsEmpty = true;
      } else {
        this.ui.noOfResults = toimipaikatResp.count;
      }
    });
  }

  updateLabelTranslations(): void {
    this.translateService.get(['label.yes', 'label.no']).subscribe((translations: any) => {
      this.labelYes = translations['label.yes'];
      this.labelNo = translations['label.no'];
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
    return this.vardaVakajarjestajaService.getVakaJarjestajaTextForLists(lapsi);
  }

  fillLapsiFilter() {
    this.lapsiFilter.voimassaolo = this.lapsiVoimassaolo.VOIMASSA;
    this.lapsiFilter.alkamisPvm = moment();
    this.lapsiFilter.paattymisPvm = moment();
  }

  filterLapset() {
    // Filter was inactive
    if (this.lapsiFilterInactive) {
      this.lapsiFilterInactive = false;
      this.fillLapsiFilter();
    }

    if (this.lapsiFilter.rajaus === this.lapsiRajaus.NONE) {
      this.lapsiFilterInactive = true;
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

    switch (this.lapsiFilter.rajaus) {
      case this.lapsiRajaus.VAKASUHTEET:
        this.lapsiFilterString += this.translateService.instant('label.varhaiskasvatussuhteet');
        break;
      case this.lapsiRajaus.VAKAPAATOKSET:
        this.lapsiFilterString += this.translateService.instant('label.varhaiskasvatuspaatokset');
        break;
      case this.lapsiRajaus.MAKSUTIEDOT:
        this.lapsiFilterString += this.translateService.instant('label.maksutiedot');
        break;
      default:
        return;
    }

    this.lapsiFilterString += ', ';

    switch (this.lapsiFilter.voimassaolo) {
      case this.lapsiVoimassaolo.ALKANUT:
        this.lapsiFilterString += this.translateService.instant('label.alkanut').toLowerCase();
        break;
      case this.lapsiVoimassaolo.PAATTYNYT:
        this.lapsiFilterString += this.translateService.instant('label.paattynyt').toLowerCase();
        break;
      case this.lapsiVoimassaolo.VOIMASSA:
        this.lapsiFilterString += this.translateService.instant('label.voimassa').toLowerCase();
        break;
      default:
        return;
    }

    this.lapsiFilterString += ', ' + this.translateService.instant('label.aikavali').toLowerCase() + ' ';
    this.lapsiFilterString += this.lapsiFilter.alkamisPvm.format(VardaDateService.vardaDefaultDateFormat) + ' - '
      + this.lapsiFilter.paattymisPvm.format(VardaDateService.vardaDefaultDateFormat);
  }

  clearLapsiFilter() {
    this.lapsiFilter.rajaus = this.lapsiRajaus.NONE;
    this.lapsiFilter.voimassaolo = null;
    this.lapsiFilter.alkamisPvm = null;
    this.lapsiFilter.paattymisPvm = null;
    this.lapsiFilterInactive = true;
    this.searchLapsi();
  }

  lapsiFiltersAreFilled(): boolean {
    return this.lapsiFilter.rajaus !== this.lapsiRajaus.NONE && this.lapsiFilter.rajaus !== null &&
      this.lapsiFilter.voimassaolo !== null && this.lapsiFilter.alkamisPvm !== null &&
      this.lapsiFilter.paattymisPvm !== null;
  }

  ngOnInit() {
    setTimeout(() => {
      this.vakajarjestajaToimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat();
      this.toimipaikanLapsetSelectedToimipaikka = this.vakajarjestajaToimipaikat.katselijaToimipaikat[0];
      forkJoin([
        this.vardaApiWrapperService.getToimipaikkaFormFieldSets(),
        this.vardaApiWrapperService.getVarhaiskasvatuspaatosFieldSets(),
      ]).pipe(mergeMap((data) => {
        this.toimipaikatFieldSets = data[0][0].fieldsets;
        this.toimintapainotuksetFieldSets = data[0][2].fieldsets;
        this.varhaiskasvatuspaatoksetFieldSets = data[1]['fieldsets'];
        return this.getToimipaikatForReporting(null, null);
      })).subscribe({
        next: this.updateToimipaikat.bind(this),
        error: () => {
          this.ui.reportingInitializationError = true;
        },
      });
    });
    this.filterLapset();
  }

  ngOnDestroy(): void {
    this.resizeSubscription.unsubscribe();
  }
}
