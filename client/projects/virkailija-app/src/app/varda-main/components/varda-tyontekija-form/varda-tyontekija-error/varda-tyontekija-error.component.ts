import { Component, OnInit, Input, SimpleChanges, ViewChild, ElementRef, OnDestroy, OnChanges } from '@angular/core';
import { BehaviorSubject, Subscription } from 'rxjs';
import { ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';


@Component({
  selector: 'app-varda-tyontekija-error',
  templateUrl: './varda-tyontekija-error.component.html',
  styleUrls: ['./varda-tyontekija-error.component.css']
})
export class VardaTyontekijaErrorComponent implements OnInit, OnDestroy {
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
