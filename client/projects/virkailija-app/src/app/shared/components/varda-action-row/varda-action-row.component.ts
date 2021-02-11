import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { BehaviorSubject } from 'rxjs';

@Component({
  selector: 'app-varda-action-row',
  templateUrl: './varda-action-row.component.html',
  styleUrls: ['./varda-action-row.component.css']
})
export class VardaActionRowComponent {
  @Input() saveDisabled: boolean;
  @Input() saveAccess: boolean;
  @Input() formExists: boolean;
  @Input() isEdit: boolean;
  @Input() noToggle: boolean; // will not hide the form after cancel
  @Input() noMargin: boolean;
  @Input() noDelete: boolean;
  @Output() togglePanel = new EventEmitter<boolean>(true);
  @Output() deleteForm = new EventEmitter<boolean>(true);
  @Output() enableEdit = new EventEmitter<boolean>(true);
  @Output() disableEdit = new EventEmitter<boolean>(true);
  i18n = VirkailijaTranslations;
  promptDelete = false;

  _togglePanel(open: boolean) {
    this.promptDelete = false;
    this.togglePanel.emit(open);
  }

  _deleteForm() {
    this.deleteForm.emit();
  }

  _enableEdit() {
    this.enableEdit.emit();
  }

  _disableEdit() {
    this.disableEdit.emit();
  }

}
