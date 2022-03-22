import { Component, QueryList } from '@angular/core';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';

@Component({
  template: ''
})
export abstract class VardaFormListAbstractComponent {
  abstract objectElements: QueryList<any>;

  i18n = VirkailijaTranslations;
  expandPanel = true;
  addObjectBoolean: boolean;
  numberOfDisplayed = 0;

  protected constructor() { }

  togglePanel(open: boolean) {
    this.expandPanel = open;
  }

  initObject() {
    this.addObjectBoolean = true;
    setTimeout(() => this.togglePanel(true), 0);
    setTimeout(() => this.objectElements.last.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  hideAddObject() {
    this.addObjectBoolean = false;
  }
}
