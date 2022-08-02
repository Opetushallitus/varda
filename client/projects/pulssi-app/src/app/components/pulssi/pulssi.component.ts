import { Component, OnDestroy, OnInit } from '@angular/core';
import { interval, Subscription } from 'rxjs';
import { KoodistoEnum } from 'varda-shared';
import { PulssiDto } from '../../models/pulssi-dto';
import { ApiService } from '../../services/api.service';
import { environment } from '../../../environments/environment';
import { PulssiTranslations } from '../../../assets/i18n/translations.enum';

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

  private updateInterval = interval(1000 * 60 * 10);
  private subscriptions: Array<Subscription> = [];

  constructor(private apiService: ApiService) {
    this.isProduction = environment.production;
  }

  ngOnInit(): void {
    this.getPulssi();
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
          this.pulssiData = data;
          // Get data again in 10 minutes
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
}
