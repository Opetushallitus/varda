import { Component, OnInit, OnDestroy, QueryList, ViewChild } from '@angular/core';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { sortByAlkamisPvm } from '../../../utilities/helper-functions';
import { Subscription } from 'rxjs';
import { VardaShowMoreLessComponent } from '../../../shared/components/varda-show-more-less/varda-show-more-less.component';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../utilities/models/enums/model-name.enum';

@Component({
  template: ''
})
export abstract class VardaFormListAbstractComponent<T extends {id?: number}> implements OnInit, OnDestroy {
  @ViewChild(VardaShowMoreLessComponent) showMoreLessComponent: VardaShowMoreLessComponent;
  abstract objectElements: QueryList<any>;

  objectList: Array<T>;
  i18n = VirkailijaTranslations;
  expandPanel = true;
  addObjectBoolean: boolean;
  numberOfDisplayed = 0;
  baseObject: any = null;
  modelName: ModelNameEnum;

  sortByFunction = sortByAlkamisPvm;

  protected subscriptions: Array<Subscription> = [];

  protected constructor(protected utilityService: VardaUtilityService) { }

  ngOnInit() {
    this.subscriptions.push(
      this.utilityService.getFocusObjectSubject().subscribe(focusObject => {
        if (focusObject?.type === this.modelName && this.objectList) {
          this.showUntil(this.objectList.findIndex(object => object.id === focusObject.id));
        }
      })
    );
  }

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
    this.utilityService.setFocusObjectSubject({type: this.modelName, id: object.id});
  }

  deleteObject(objectId: number) {
    this.objectList = this.objectList.filter(obj => obj.id !== objectId);
    this.updateActiveObject();
    this.utilityService.setFocusObjectSubject(null);
  }

  showUntil(index: number) {
    if (index !== -1 && this.numberOfDisplayed < index + 1) {
      this.showMoreLessComponent?.showMore();
      setTimeout(() => this.showUntil(index), 100);
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  abstract updateActiveObject();
}
