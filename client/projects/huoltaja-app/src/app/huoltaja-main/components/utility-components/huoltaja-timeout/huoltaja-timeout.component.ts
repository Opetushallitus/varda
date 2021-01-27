import { Component, Inject, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { MAT_SNACK_BAR_DATA } from '@angular/material/snack-bar';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { BehaviorSubject, interval, Subscription } from 'rxjs';

export interface TimeoutData {
  seconds: number;
  dismiss: () => {};
}

@Component({
  selector: 'app-huoltaja-timeout',
  templateUrl: './huoltaja-timeout.component.html',
  styleUrls: ['./huoltaja-timeout.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class HuoltajaTimeoutComponent implements OnInit, OnDestroy {
  i18n = HuoltajaTranslations;
  seconds = new BehaviorSubject<number>(null);
  subscriptions: Array<Subscription> = [];
  constructor(
    @Inject(MAT_SNACK_BAR_DATA) private data: TimeoutData
  ) {
    this.seconds.next(data.seconds);
  }

  ngOnInit(): void {
    this.subscriptions.push(
      interval(1000).subscribe(val => this.seconds.next(this.data.seconds - val)),
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  dismiss() {
    this.data.dismiss();
  }
}
