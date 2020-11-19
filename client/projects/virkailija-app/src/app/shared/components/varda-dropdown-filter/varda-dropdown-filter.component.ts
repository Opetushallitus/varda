import { Component, OnInit, Input, ViewChild, EventEmitter, Output, ElementRef, OnDestroy } from '@angular/core';
import { MatMenuTrigger } from '@angular/material/menu';
import { fromEvent, Subject, Subscription } from 'rxjs';
import { debounceTime } from 'rxjs/operators';


@Component({
  selector: 'app-varda-dropdown-filter',
  templateUrl: './varda-dropdown-filter.component.html',
  styleUrls: ['./varda-dropdown-filter.component.css']
})
export class VardaDropdownFilterComponent implements OnInit, OnDestroy {
  @Input() filterBy: Array<string>;
  @Input() list: Array<object>;
  @Input() label: string;
  @Input() ariaLabel: string;
  @Input() placeholder: string;
  @Input() noResults: string;
  @Output() select = new EventEmitter(true);
  @ViewChild('dropdownFilterInput') dropdownFilterInput: ElementRef;
  @ViewChild(MatMenuTrigger, { static: true }) trigger: MatMenuTrigger;
  subscriptions: Array<Subscription> = [];
  showDropdown: boolean;
  filteredList: Array<object>;
  filterText = '';
  searchFieldChanged = new Subject<boolean>();

  constructor() { }

  ngOnInit() {
    this.filteredList = this.list;
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
    this.filteredList = this.list.filter(item => {
      return this.filterBy.some(key => item[key] && item[key].toLowerCase().includes(text));
    });

    if (this.filteredList.length === 1 && enter) {
      setTimeout(() => this.selectItem(this.filteredList[0]), 500);
    }
  }

  selectItem(item: any) {
    this.select.emit(item);
    this.trigger.closeMenu();
  }
}
