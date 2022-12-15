import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
  ViewChild,
  ViewEncapsulation
} from '@angular/core';
import { MatLegacyMenuTrigger as MatMenuTrigger } from '@angular/material/legacy-menu';
import { Subject, Subscription } from 'rxjs';
import { debounceTime } from 'rxjs/operators';


@Component({
  selector: 'app-varda-dropdown-filter',
  templateUrl: './varda-dropdown-filter.component.html',
  styleUrls: ['./varda-dropdown-filter.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class VardaDropdownFilterComponent<T> implements OnInit, OnDestroy {
  @Input() filterBy: Array<string>;
  @Input() list: Array<{name?: string; className?: string; items: Array<T>}>;
  @Input() label: string;
  @Input() ariaLabel: string;
  @Input() placeholder: string;
  @Input() noResults: string;
  @Output() valueSelected = new EventEmitter(true);
  @ViewChild('dropdownFilterInput') dropdownFilterInput: ElementRef;
  @ViewChild(MatMenuTrigger, { static: true }) trigger: MatMenuTrigger;
  subscriptions: Array<Subscription> = [];
  showDropdown: boolean;
  filteredList: Array<{name?: string; className?: string; items: Array<T>}>;
  filterText = '';
  searchFieldChanged = new Subject<boolean>();
  totalCount = 0;

  constructor() { }

  ngOnInit() {
    this.filteredList = this.list;
    this.list.forEach(group => {
      this.totalCount += group.items.length;
    });

    this.trigger.menuClosed.subscribe({
      next: closed => this.showDropdown = false,
      error: err => console.error(err),
    });


    this.trigger.menuOpened.subscribe({
      next: opened => this.dropdownFilterInput ?
        setTimeout(() => this.dropdownFilterInput.nativeElement.focus(), 300) : null,
      error: err => console.error(err),
    });

    this.subscriptions.push(this.searchFieldChanged.pipe(debounceTime(500)).subscribe((enter: boolean) => this.filterList(this.filterText, enter)));

  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  debounceList(text: string, enter = false) {
    this.searchFieldChanged.next(enter);

  }

  filterList(text: string, enter: boolean = false) {
    setTimeout(() => this.dropdownFilterInput.nativeElement.focus(), 200);
    if (!text || !text.length) {
      return this.filteredList = this.list;
    }
    text = text.toLowerCase().trim();

    let resultCount = 0;
    this.filteredList = this.list.reduce((reducedList, originalGroup) => {
      // Make a copy of the original group
      const group = {...originalGroup};
      group.items = group.items.filter(item => this.filterBy.some(key => item[key] && item[key].toLowerCase().includes(text)));
      if (group.items.length > 0) {
        reducedList.push(group);
        resultCount += group.items.length;
      }
      return reducedList;
    }, []);

    if (resultCount === 1 && enter) {
      setTimeout(() => this.selectItem(this.filteredList[0].items[0]), 500);
    }
  }

  selectItem(item: any) {
    this.valueSelected.emit(item);
    this.trigger.closeMenu();
  }
}
