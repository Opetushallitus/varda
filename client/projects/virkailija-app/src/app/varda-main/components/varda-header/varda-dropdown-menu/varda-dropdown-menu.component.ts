import {Component, EventEmitter, Input, OnInit, Output, ViewChild} from '@angular/core';
import {MatMenuTrigger} from '@angular/material/menu';

@Component({
  selector: 'app-varda-dropdown-menu',
  templateUrl: './varda-dropdown-menu.component.html',
  styleUrls: ['./varda-dropdown-menu.component.css']
})
export class VardaDropdownMenuComponent implements OnInit {
  @Input() topicKey: string;
  @Input() routeMaps: Array<{route: string, textKey: string, isHidden: boolean}>;
  @ViewChild(MatMenuTrigger, { static: true }) trigger: MatMenuTrigger;
  @Output() navigationChange = new EventEmitter(true);
  showDropdown: boolean;

  constructor() { }

  ngOnInit() {
    this.trigger.menuClosed.subscribe({
      next: closed => this.showDropdown = false,
      error: err => console.error(err),
    });
  }

  setActiveNavItem() {
    this.navigationChange.emit();
  }
}
