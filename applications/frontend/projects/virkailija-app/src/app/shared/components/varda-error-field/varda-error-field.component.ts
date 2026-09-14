import { Component, OnInit, Input, ViewChild, ElementRef, OnDestroy } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { BehaviorSubject, Subscription } from 'rxjs';
import { ErrorTree } from '../../../core/services/varda-error-message.service';



@Component({
    selector: 'app-varda-error-field',
    templateUrl: './varda-error-field.component.html',
    styleUrls: ['./varda-error-field.component.css'],
    standalone: false
})
export class VardaErrorFieldComponent implements OnInit, OnDestroy {
  @Input() errors: BehaviorSubject<Array<ErrorTree>>;
  @ViewChild('scrollTo', { static: false }) scrollTo: ElementRef;
  i18n = VirkailijaTranslations;
  subscription: Subscription;

  constructor() { }

  ngOnInit() {
    this.subscription = this.errors.subscribe(change => {
      if (change?.length) {
        setTimeout(() => this.scrollTo.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
      }
    });
  }

  ngOnDestroy() {
    this.subscription?.unsubscribe();
  }

  hideError() {
    this.errors.next([]);
  }
}
