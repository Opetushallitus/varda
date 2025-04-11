import {Component, Input, OnDestroy, OnInit} from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import {Observable, Subscription} from 'rxjs';

@Component({
  selector: 'app-varda-error-alert',
  templateUrl: './varda-error-alert.component.html',
  styleUrls: ['./varda-error-alert.component.css']
})
export class VardaErrorAlertComponent implements OnInit, OnDestroy {
  @Input() errorMessageKey$: Observable<string>;
  isOpen: boolean;
  i18n = VirkailijaTranslations;
  errorMessageSubscription: Subscription;
  errorMessageKey: string;

  constructor() {
    this.isOpen = true;
  }

  ngOnInit() {
    this.errorMessageKey = '';
    this.errorMessageSubscription = this.errorMessageKey$.subscribe(errorMessageKey => {
      this.errorMessageKey = errorMessageKey;
      this.isOpen = true;
    });
  }

  ngOnDestroy(): void {
    this.errorMessageSubscription.unsubscribe();
  }

}
