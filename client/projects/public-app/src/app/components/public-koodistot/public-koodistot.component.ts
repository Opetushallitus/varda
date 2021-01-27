import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subject, Subscription, BehaviorSubject } from 'rxjs';
import { Router } from '@angular/router';
import { PublicKoodistotService } from '../../services/public-koodistot.service';
import { PublicResponsiveService } from '../../services/public-responsive.service';
import { PublicTranslations } from 'projects/public-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-public-koodistot',
  templateUrl: './public-koodistot.component.html',
  styleUrls: ['./public-koodistot.component.css']
})
export class PublicKoodistotComponent implements OnInit, OnDestroy {
  translation = PublicTranslations;
  koodistoNames: Subject<Array<string>>;
  isSmall: BehaviorSubject<boolean>;
  selectedKoodisto: string;
  private subscriptions: Array<Subscription> = [];

  constructor(private router: Router, private publicKoodistotService: PublicKoodistotService,
              private responsiveService: PublicResponsiveService) { }

  ngOnInit(): void {
    this.koodistoNames = this.publicKoodistotService.getKoodistoNames();
    this.isSmall = this.responsiveService.getIsSmall();
    this.subscriptions.push(
      this.publicKoodistotService.getSelectedKoodisto().subscribe(value => {
        // https://indepth.dev/everything-you-need-to-know-about-the-expressionchangedafterithasbeencheckederror-error/
        setTimeout(() => {
          this.selectedKoodisto = value;
        });
      })
    );
  }

  selectKoodisto(value: string) {
    this.router.navigateByUrl(`/koodistot/${value}`);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => {
      subscription.unsubscribe();
    });
    this.publicKoodistotService.updateSelectedKoodisto('');
  }
}
