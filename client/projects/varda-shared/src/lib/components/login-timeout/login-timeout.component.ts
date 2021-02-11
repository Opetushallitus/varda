import { Component, Inject, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { MAT_SNACK_BAR_DATA } from '@angular/material/snack-bar';
import { BehaviorSubject, interval, Subscription } from 'rxjs';

export interface TimeoutData {
  reasonText: string;
  counterText: string;
  actionText: string;
  seconds: number;
  dismiss?: () => {};
}

export enum TimeoutTranslationKey {
  timeout_inactive_text = 'timeout.inactive-text',
  timeout_logout_seconds_COUNT = 'timeout.logout-seconds-COUNT',
  timeout_action_text = 'timeout.action-text',
  timeout_expired_text = 'timeout.expired.text',
  timeout_expired_close_seconds_COUNT = 'timeout.expired.close-seconds-COUNT',
  timeout_expired_action_text = 'timeout.expired.action-text',
}

@Component({
  selector: 'lib-login-timeout',
  templateUrl: './login-timeout.component.html',
  styleUrls: ['./login-timeout.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class LoginTimeoutComponent implements OnInit, OnDestroy {
  private counterText: string;
  reasonText: string;
  actionText: string;
  visibleCounterText: string;
  seconds = new BehaviorSubject<number>(null);
  subscriptions: Array<Subscription> = [];

  constructor(
    @Inject(MAT_SNACK_BAR_DATA) private data: TimeoutData
  ) {
    this.seconds.next(data.seconds);
    this.reasonText = data.reasonText;
    this.counterText = data.counterText;
    this.actionText = data.actionText;
  }

  ngOnInit(): void {
    const countReplacement = '{{ count }}';
    this.visibleCounterText = this.counterText?.replace(countReplacement, this.data.seconds.toString());

    this.subscriptions.push(
      interval(1000).subscribe(val => {
        const currentSeconds = this.data.seconds - (val + 1);
        this.seconds.next(currentSeconds);
        this.visibleCounterText = this.counterText?.replace(countReplacement, currentSeconds.toString());
      }),
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  dismiss() {
    this.data.dismiss();
  }
}
