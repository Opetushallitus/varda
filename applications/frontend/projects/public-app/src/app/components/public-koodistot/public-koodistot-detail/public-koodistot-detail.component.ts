import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, ParamMap } from '@angular/router';
import { PublicKoodistotService } from '../../../services/public-koodistot.service';
import { KoodistoDto } from '../../../models/koodisto-dto';
import { CodeDto } from '../../../models/code-dto';
import { DateTime } from 'luxon';
import { BehaviorSubject } from 'rxjs';
import { PublicTranslations } from 'projects/public-app/src/assets/i18n/translations.enum';
import { ResponsiveService } from 'varda-shared';

@Component({
    selector: 'app-public-koodistot-detail',
    templateUrl: './public-koodistot-detail.component.html',
    styleUrls: ['./public-koodistot-detail.component.css'],
    standalone: false
})
export class PublicKoodistotDetailComponent implements OnInit, OnDestroy {
  translation = PublicTranslations;
  selectedKoodistoName: string = null;
  isValidKoodistoName = false;
  codes: Array<CodeDto> = [];
  codesPassive: Array<CodeDto> = [];
  version = 0;
  update_datetime = DateTime.now();
  isExtraSmall: BehaviorSubject<boolean>;
  private koodistot: Array<KoodistoDto> = [];
  private subscriptions = [];

  constructor(private activatedRoute: ActivatedRoute, private publicKoodistotService: PublicKoodistotService,
              private responsiveService: ResponsiveService) { }

  ngOnInit(): void {
    this.isExtraSmall = this.responsiveService.getIsExtraSmall();
    this.subscriptions.push(
      this.publicKoodistotService.getKoodistot().subscribe(data => {
        this.koodistot = data;
        if (this.selectedKoodistoName) {
          this.displayKoodisto();
        }
      }),
      this.activatedRoute.paramMap.subscribe((params: ParamMap) => {
        this.selectedKoodistoName = params.get('koodisto');
        this.publicKoodistotService.updateSelectedKoodisto(this.selectedKoodistoName);
        this.displayKoodisto();
      })
    );
  }

  showSubheader(code: CodeDto) {
    if (this.selectedKoodistoName !== 'vardavirheviestit') {
      return false;
    }

    const codeIndex = this.codes.indexOf(code);
    const previousValue = codeIndex === 0 ? '' : this.codes[codeIndex - 1].code_value;
    if (code.code_value.substring(0, 2) !== previousValue.substring(0, 2)) {
      // Code category is different from last category, add a subheader
      return true;
    }
  }

  getSubheaderTranslationKey(code: CodeDto) {
    return `koodistot.subheading.${code.code_value.substring(0, 2).toLowerCase()}`;
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(subscription => {
      subscription.unsubscribe();
    });
  }

  private displayKoodisto() {
    const koodistoIndex = this.publicKoodistotService.getKoodistoIndex(this.selectedKoodistoName);
    if (koodistoIndex !== -1) {
      this.isValidKoodistoName = true;
      const koodisto = this.koodistot[koodistoIndex];
      this.codes = koodisto.codes.filter(code => code.active);
      this.codesPassive = koodisto.codes.filter(code => !code.active);
      this.version = koodisto.version;
      this.update_datetime = DateTime.fromISO(koodisto.update_datetime);
    }
  }
}
