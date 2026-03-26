import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewEncapsulation } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VIEW_INITIAL_COUNT, VIEW_LESS_COUNT, VIEW_MORE_COUNT } from '../../../utilities/constants';

@Component({
    selector: 'app-varda-show-more-less',
    templateUrl: './varda-show-more-less.component.html',
    styleUrls: ['./varda-show-more-less.component.css'],
    encapsulation: ViewEncapsulation.None,
    standalone: false
})
export class VardaShowMoreLessComponent implements OnChanges {
  @Input() numberOfDisplayed: number;
  @Input() numberOfItems: number;
  @Input() showMoreKey: string;
  @Output() numberOfDisplayedChange = new EventEmitter<number>();

  VIEW_INITIAL_COUNT = VIEW_INITIAL_COUNT;
  i18n = VirkailijaTranslations;

  constructor() { }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.numberOfItems) {
      this.numberOfDisplayed = this.numberOfItems >= VIEW_INITIAL_COUNT ? VIEW_INITIAL_COUNT : this.numberOfItems;
      setTimeout(() => this.numberOfDisplayedChange.emit(this.numberOfDisplayed));
    }
  }

  showMore() {
    const proposedCount = this.numberOfDisplayed + VIEW_MORE_COUNT;
    this.numberOfDisplayed = proposedCount <= this.numberOfItems ? proposedCount : this.numberOfItems;
    setTimeout(() => this.numberOfDisplayedChange.emit(this.numberOfDisplayed));
  }

  showLess() {
    const proposedCount = this.numberOfDisplayed - VIEW_LESS_COUNT;
    if (proposedCount <= VIEW_INITIAL_COUNT) {
      this.numberOfDisplayed = this.numberOfItems >= VIEW_INITIAL_COUNT ? VIEW_INITIAL_COUNT : this.numberOfItems;
    } else {
      this.numberOfDisplayed = proposedCount;
    }
    setTimeout(() => this.numberOfDisplayedChange.emit(this.numberOfDisplayed));
  }
}
