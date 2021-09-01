import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-tiedonsiirto-filter-header',
  templateUrl: './tiedonsiirto-filter-header.component.html',
  styleUrls: ['./tiedonsiirto-filter-header.component.css']
})
export class TiedonsiirtoFilterHeaderComponent implements OnInit {
  @Input() label: string;
  @Input() multiline: boolean;
  @Input() hideSearchButton = false;
  @Output() resetFilter = new EventEmitter<boolean>(true);
  @Output() submitFilter = new EventEmitter<boolean>(true);
  @Output() emitToggle = new EventEmitter<boolean>(true);

  i18n = VirkailijaTranslations;
  expand = false;

  constructor() { }

  ngOnInit(): void {
  }

  toggle() {
    this.expand = !this.expand;
    if (!this.expand) {
      this.resetFilter.emit(true);
      this.submitFilter.emit(true);
    }
    this.emitToggle.emit(this.expand);
  }
}
