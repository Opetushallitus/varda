import { Component, Input, Output, EventEmitter } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';


@Component({
    selector: 'app-varda-delete-henkilo',
    templateUrl: './varda-delete-henkilo.component.html',
    styleUrls: ['./varda-delete-henkilo.component.css'],
    standalone: false
})
export class VardaDeleteHenkiloComponent {
  @Input() instructionText: string;
  @Input() deleteText: string;
  @Output() deleteAction = new EventEmitter<void>(true);
  i18n = VirkailijaTranslations;
  promptDeleteHenkilo = 0;

  constructor() { }

  deleteEmit() {
    this.deleteAction.emit();
  }
}
