import { Component, OnInit } from '@angular/core';
import { VardaLocalstorageWrapperService } from '../../../core/services/varda-localstorage-wrapper.service';
import { VardaDomService } from '../../../core/services/varda-dom.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

declare var $: any;

@Component({
  selector: 'app-varda-accessibility-settings',
  templateUrl: './varda-accessibility-settings.component.html',
  styleUrls: ['./varda-accessibility-settings.component.css']
})
export class VardaAccessibilitySettingsComponent implements OnInit {
  i18n = VirkailijaTranslations;
  highContrastEnabled: boolean;
  displayAccessibilitySettings: boolean;
  documentRootElem: any;
  documentRootFontSize: number;
  instructionPanelContentElem: any;
  instructionPanelHeaderElem: any;

  constructor(private vardaLocalstorageWrapperService: VardaLocalstorageWrapperService, private vardaDomService: VardaDomService) {
    this.highContrastEnabled = false;
    this.displayAccessibilitySettings = false;
    this.documentRootFontSize = 16;
  }

  closeAccessibilitySettings(): void {
    this.displayAccessibilitySettings = false;
    this.vardaLocalstorageWrapperService.saveAccessibilitySettingsVisibility(false);
  }

  toggleContrast(isEnabled: boolean): void {
    this.highContrastEnabled = isEnabled;
    this.vardaLocalstorageWrapperService.saveContrastSelection(this.highContrastEnabled);
  }

  increaseFontSize(): void {
    this.documentRootFontSize++;
    if (this.documentRootFontSize > 30) {
      this.documentRootFontSize = 30;
    }
    this.documentRootElem.style.fontSize = `${this.documentRootFontSize}px`;
    this.instructionPanelHeaderElem?.css({'fontSize': `${this.documentRootFontSize}px`});
    this.instructionPanelContentElem?.css({'fontSize': `${this.documentRootFontSize}px`});
  }

  decreaseFontSize(): void {
    this.documentRootFontSize--;
    if (this.documentRootFontSize < 16) {
      this.documentRootFontSize = 16;
    }
    this.documentRootElem.style.fontSize = `${this.documentRootFontSize}px`;
    this.instructionPanelHeaderElem?.css({'fontSize': `${this.documentRootFontSize}px`});
    this.instructionPanelContentElem?.css({'fontSize': `${this.documentRootFontSize}px`});
  }

  ngOnInit() {
    this.vardaLocalstorageWrapperService.highContrastIsEnabled().subscribe((isEnabled) => {
      this.highContrastEnabled = isEnabled;
    });

    this.vardaLocalstorageWrapperService.showAccessibilitySettings().subscribe((isOn) => {
      this.displayAccessibilitySettings = isOn;
    });

    this.vardaDomService.initInstructionsSubject.asObservable().subscribe(() => {
      this.instructionPanelHeaderElem = $('.mat-expansion-panel-header');
      this.instructionPanelContentElem = $('.mat-expansion-panel-content');
    });

    this.documentRootElem = document.documentElement;
    const initialFontSize = window.getComputedStyle(this.documentRootElem).fontSize;
    this.documentRootFontSize = parseInt(initialFontSize.substring(0, 2));
  }

}
