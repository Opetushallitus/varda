import { Component, QueryList } from '@angular/core';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { sortByAlkamisPvm } from '../../../utilities/helper-functions';

@Component({
  template: ''
})
export abstract class VardaFormListAbstractComponent<T extends {id?: number}> {
  abstract objectElements: QueryList<any>;

  objectList: Array<T>;
  i18n = VirkailijaTranslations;
  expandPanel = true;
  addObjectBoolean: boolean;
  numberOfDisplayed = 0;
  baseObject: any = null;

  sortByFunction = sortByAlkamisPvm;

  protected constructor() { }

  togglePanel(open: boolean) {
    this.expandPanel = open;
  }

  initObject() {
    this.addObjectBoolean = true;
    setTimeout(() => this.togglePanel(true), 0);
    setTimeout(() => this.objectElements.last.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  setBaseObject(object: T) {
    const deepCopy = JSON.parse(JSON.stringify(object));
    deepCopy.id = null;
    if (deepCopy.hasOwnProperty('alkamis_pvm')) {
      delete deepCopy.alkamis_pvm;
    }
    if (deepCopy.hasOwnProperty('paattymis_pvm')) {
      delete deepCopy.paattymis_pvm;
    }
    this.baseObject = deepCopy;
    this.initObject();
  }

  hideAddObject() {
    this.addObjectBoolean = false;
    this.baseObject = null;
  }

  addObject(object: T) {
    this.objectList = this.objectList.filter(obj => obj.id !== object.id);
    this.objectList.push(object);
    this.objectList = this.objectList.sort(this.sortByFunction);
    this.updateActiveObject();
  }

  deleteObject(objectId: number) {
    this.objectList = this.objectList.filter(obj => obj.id !== objectId);
    this.updateActiveObject();
  }

  abstract updateActiveObject();
}
