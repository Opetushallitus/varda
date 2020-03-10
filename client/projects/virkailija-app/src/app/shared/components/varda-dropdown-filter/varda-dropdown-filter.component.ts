import { Component, OnInit, Input, ViewChild, EventEmitter, Output, ElementRef } from '@angular/core';
import { MatMenuTrigger } from '@angular/material/menu';


@Component({
  selector: 'app-varda-dropdown-filter',
  templateUrl: './varda-dropdown-filter.component.html',
  styleUrls: ['./varda-dropdown-filter.component.css']
})
export class VardaDropdownFilterComponent implements OnInit {
  @Input() filterBy: Array<string>;
  @Input() list: Array<object>;
  @Input() label: string;
  @Input() ariaLabel: string;
  @Output() onSelect = new EventEmitter(true);
  @ViewChild("dropdownFilterInput") dropdownFilterInput: ElementRef;
  @ViewChild(MatMenuTrigger, { static: true }) trigger: MatMenuTrigger;
  showDropdown: boolean;
  filteredList: Array<object>;
  filterText: string;

  constructor() { }

  ngOnInit() {
    this.filteredList = this.list;
    this.trigger.menuClosed.subscribe({
      next: closed => this.showDropdown = false,
      error: err => console.error(err),
    });


    this.trigger.menuOpened.subscribe({
      next: opened => this.dropdownFilterInput ?
        setTimeout(() => this.dropdownFilterInput.nativeElement.focus(), 500) : null,
      error: err => console.error(err),
    });
  }


  filterList(text: string, enter: boolean = false) {
    setTimeout(() => this.dropdownFilterInput.nativeElement.focus(), 100);
    if (!text || !text.length)
      return this.filteredList = this.list
    text = text.toLowerCase().trim()
    this.filteredList = this.list.filter(item => {
      return this.filterBy.some(key => item[key] && item[key].toLowerCase().includes(text))
    });

    if (this.filteredList.length === 1 && enter)
      setTimeout(() => this.selectItem(this.filteredList[0]), 500);
  }

  selectItem(item: any) {
    this.onSelect.emit(item);
    this.trigger.closeMenu();
  }
}
