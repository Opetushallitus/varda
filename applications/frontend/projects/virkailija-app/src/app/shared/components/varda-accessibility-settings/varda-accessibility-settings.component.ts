import { AfterViewInit, Component, OnInit, Renderer2, ViewChildren, QueryList, ElementRef  } from '@angular/core';
import { VardaAccessibilityService } from '../../../core/services/varda-accessibility.service';
import { VardaDomService } from '../../../core/services/varda-dom.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
    selector: 'app-varda-accessibility-settings',
    templateUrl: './varda-accessibility-settings.component.html',
    styleUrls: ['./varda-accessibility-settings.component.css'],
    standalone: false
})
export class VardaAccessibilitySettingsComponent implements OnInit, AfterViewInit {
  // Use ElementRef to get the native elements
  @ViewChildren('panelHeader', { read: ElementRef }) panelHeaders: QueryList<ElementRef>;
  @ViewChildren('panelContent', { read: ElementRef }) panelContents: QueryList<ElementRef>;

  i18n = VirkailijaTranslations;
  highContrastEnabled: boolean;
  displayAccessibilitySettings: boolean;
  documentRootFontSize: number;
  minFontSize = 16;
  maxFontSize = 26;

  constructor(
    private accessibilityService: VardaAccessibilityService,
    private vardaDomService: VardaDomService,
    private renderer: Renderer2
  ) {
    this.highContrastEnabled = false;
    this.displayAccessibilitySettings = false;
    this.documentRootFontSize = this.minFontSize;
  }

  private get documentRootElem(): HTMLElement {
    return document.documentElement;
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
      this.renderer.setStyle(this.documentRootElem, 'font-size', `${fontSize}px`);

      // Update panel elements font size
      this.updatePanelsFontSize(fontSize);
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
      // Panel elements will be available through ViewChildren
      this.updatePanelsFontSize(this.documentRootFontSize);
    });

    const initialFontSize = window.getComputedStyle(this.documentRootElem).fontSize;
    this.documentRootFontSize = parseInt(initialFontSize.substring(0, 2), 10);
  }

  private updatePanelsFontSize(fontSize: number): void {
    this.panelHeaders?.forEach(header => {
      this.renderer.setStyle(header.nativeElement, 'font-size', `${fontSize}px`);
    });

    // Update content
    this.panelContents?.forEach(content => {
      this.renderer.setStyle(content.nativeElement, 'font-size', `${fontSize}px`);
    });
  }

}
