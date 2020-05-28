import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, ParamMap } from '@angular/router';
import { PublicKoodistotService } from '../../../services/public-koodistot.service';
import { KoodistoDto } from '../../../models/koodisto-dto';
import { CodeDto } from '../../../models/code-dto';
import * as moment from 'moment';
import { PublicResponsiveService } from '../../../services/public-responsive.service';
import { BehaviorSubject } from 'rxjs';

@Component({
  selector: 'app-public-koodistot-detail',
  templateUrl: './public-koodistot-detail.component.html',
  styleUrls: ['./public-koodistot-detail.component.css']
})
export class PublicKoodistotDetailComponent implements OnInit, OnDestroy {
  selectedKoodistoName: string = null;
  isValidKoodistoName = false;
  private koodistot: Array<KoodistoDto> = [];
  codes: Array<CodeDto> = [];
  version = 0;
  update_datetime = moment();
  private subscriptions = [];
  isExtraSmall: BehaviorSubject<boolean>;

  constructor(private activatedRoute: ActivatedRoute, private publicKoodistotService: PublicKoodistotService,
              private responsiveService: PublicResponsiveService) { }

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

  private displayKoodisto() {
    const koodistoIndex = this.publicKoodistotService.getKoodistoIndex(this.selectedKoodistoName);
    if (koodistoIndex !== -1) {
      this.isValidKoodistoName = true;
      const koodisto = this.koodistot[koodistoIndex];
      this.codes = koodisto.codes;
      this.version = koodisto.version;
      this.update_datetime = moment(koodisto.update_datetime);
    }
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(subscription => {
      subscription.unsubscribe();
    });
  }

}
