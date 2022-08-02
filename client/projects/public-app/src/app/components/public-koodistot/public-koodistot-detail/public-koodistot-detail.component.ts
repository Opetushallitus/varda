import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, ParamMap } from '@angular/router';
import { PublicKoodistotService } from '../../../services/public-koodistot.service';
import { KoodistoDto } from '../../../models/koodisto-dto';
import { CodeDto } from '../../../models/code-dto';
import * as moment from 'moment';
import { BehaviorSubject } from 'rxjs';
import { PublicTranslations } from 'projects/public-app/src/assets/i18n/translations.enum';
import { ResponsiveService } from 'varda-shared';

@Component({
  selector: 'app-public-koodistot-detail',
  templateUrl: './public-koodistot-detail.component.html',
  styleUrls: ['./public-koodistot-detail.component.css']
})
export class PublicKoodistotDetailComponent implements OnInit, OnDestroy {
  translation = PublicTranslations;
  selectedKoodistoName: string = null;
  isValidKoodistoName = false;
  codes: Array<CodeDto> = [];
  codesPassive: Array<CodeDto> = [];
  version = 0;
  update_datetime = moment();
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
      this.update_datetime = moment(koodisto.update_datetime);
    }
  }
}
