import { Component, OnDestroy, OnInit } from '@angular/core';
import { interval, Subscription } from 'rxjs';
import { KoodistoEnum, MatomoService } from 'varda-shared';
import { PulssiDto } from '../../models/pulssi-dto';
import { ApiService } from '../../services/api.service';
import { environment } from '../../../environments/environment';
import { PulssiTranslations } from '../../../assets/i18n/translations.enum';

declare const matomoPageChange: any;

@Component({
  selector: 'app-pulssi',
  templateUrl: './pulssi.component.html',
  styleUrls: ['./pulssi.component.css']
})
export class PulssiComponent implements OnInit, OnDestroy {
  translations = PulssiTranslations;
  isProduction = false;
  pulssiData: PulssiDto;
  KoodistoEnum = KoodistoEnum;

  private updateInterval = interval(1000 * 60 * 60);
  private subscriptions: Array<Subscription> = [];

  constructor(
    private apiService: ApiService,
    private matomo: MatomoService
  ) {
    this.isProduction = environment.production;
  }

  ngOnInit(): void {
    this.initMatomoScript();
    this.getPulssi();
  }

  initMatomoScript() {
    const vardaDomains = this.apiService.getVardaDomains();
    if (!vardaDomains.some(hostname => window.location.hostname.endsWith(hostname))) {
      return false;
    }

    if (this.isProduction) {
      const node = document.createElement('script');
      document.getElementsByTagName('head')[0].appendChild(node);

      const [productionID, qaID] = [25, 26];
      this.matomo.initMatomo(vardaDomains.includes(window.location.hostname) ? productionID : qaID);
      this.setMatomoPageChange();
    }
  }

  getPulssi(refresh?: boolean) {
    this.unsubscribe();

    const params: Record<string, unknown> = {};
    if (!this.isProduction && refresh) {
      params.refresh = true;
    }

    this.subscriptions.push(
      this.apiService.getPulssi(params).subscribe({
        next: data => {
          data.toimipaikka_by_ak = Object.keys(data.toimipaikka_by_ak)
            .sort((a, b) => {
              // others key always comes last
              if (a === 'others') {
                return 1;
              } else if (b === 'others') {
                return -1;
              }
              return 0;
            }).reduce((previousValue, currentValue) => {
              // Rebuild toimipaikka_by_ak object
              previousValue[currentValue] = data.toimipaikka_by_ak[currentValue];
              return previousValue;
            }, {});

          this.pulssiData = data;
          // Get data again in 60 minutes
          this.subscriptions.push(
            this.updateInterval.subscribe(() => this.getPulssi())
          );
        },
        error: err => console.error(err)
      })
    );
  }

  unsubscribe() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
    this.subscriptions = [];
  }

  getEntries(obj: object) {
    return Object.entries(obj);
  }

  ngOnDestroy() {
    this.unsubscribe();
  }

  private setMatomoPageChange() {
    try {
      matomoPageChange('Pulssi', window.location.pathname);
    } catch (e) {
      console.log(e);
    }
  }
}
