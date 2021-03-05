import { AfterViewInit, Component, OnInit } from '@angular/core';
import { VardaAccessibilityService } from '../../../core/services/varda-accessibility.service';
import { VardaDomService } from '../../../core/services/varda-dom.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

declare var $: any;

@Component({
  selector: 'app-varda-accessibility-settings',
  templateUrl: './varda-accessibility-settings.component.html',
  styleUrls: ['./varda-accessibility-settings.component.css']
})
export class VardaAccessibilitySettingsComponent implements OnInit, AfterViewInit {
  i18n = VirkailijaTranslations;
  highContrastEnabled: boolean;
  displayAccessibilitySettings: boolean;
  documentRootElem: any;
  documentRootFontSize: number;
  instructionPanelContentElem: any;
  instructionPanelHeaderElem: any;
  minFontSize = 16;
  maxFontSize = 26;

  constructor(
    private accessibilityService: VardaAccessibilityService,
    private vardaDomService: VardaDomService
  ) {
    this.highContrastEnabled = false;
    this.displayAccessibilitySettings = false;
    this.documentRootFontSize = this.minFontSize;
  }

  closeAccessibilitySettings(): void {
    this.displayAccessibilitySettings = false;
    this.accessibilityService.saveAccessibilitySettingsVisibility(false);
  }

  toggleContrast(isEnabled: boolean): void {
    this.highContrastEnabled = isEnabled;
    this.accessibilityService.saveContrastSelection(this.highContrastEnabled);
  }

  setFontSize(fontSize: number): void {
    if (fontSize !== this.documentRootFontSize) {
      this.documentRootFontSize = fontSize;
      this.documentRootElem.style.fontSize = `${fontSize}px`;
      this.instructionPanelHeaderElem?.css({ 'fontSize': `${fontSize}px` });
      this.instructionPanelContentElem?.css({ 'fontSize': `${fontSize}px` });
      this.accessibilityService.saveFontSize(fontSize);
    }
  }

  increaseFontSize(): void {
    let fontSize = this.documentRootFontSize + 1;
    if (fontSize > this.maxFontSize) {
      fontSize = this.maxFontSize;
    }

    this.setFontSize(fontSize);
  }

  decreaseFontSize(): void {
    let fontSize = this.documentRootFontSize - 1;
    if (fontSize < this.minFontSize) {
      fontSize = this.minFontSize;
    }

    this.setFontSize(fontSize);
  }

  ngAfterViewInit() {
    this.accessibilityService.getFontSize().subscribe((fontSize) => {
      fontSize = fontSize >= this.minFontSize && fontSize <= this.maxFontSize ? fontSize : this.minFontSize;
      this.setFontSize(fontSize);
    });
  }

  ngOnInit() {
    this.accessibilityService.highContrastIsEnabled().subscribe((isEnabled) => {
      this.highContrastEnabled = isEnabled;
    });

    this.accessibilityService.showAccessibilitySettings().subscribe((isOn) => {
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
