import { Component, OnInit } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaLocalstorageWrapperService } from '../../../core/services/varda-localstorage-wrapper.service';

@Component({
  selector: 'app-varda-footer',
  templateUrl: './varda-footer.component.html',
  styleUrls: ['./varda-footer.component.css']
})
export class VardaFooterComponent implements OnInit {
  i18n = VirkailijaTranslations;
  highContrastText: string;
  highContrastEnabled: boolean;
  displayAccessibilitySettings: boolean;

  constructor(private vardaLocalStorageWrapper: VardaLocalstorageWrapperService) {
    this.highContrastText = 'Lisää kontrastia';
    this.highContrastEnabled = false;
    this.displayAccessibilitySettings = true;
  }

  toggleContrast(isEnabled: boolean): void {
    this.highContrastEnabled = isEnabled;
    this.vardaLocalStorageWrapper.saveContrastSelection(this.highContrastEnabled);
  }

  toggleAccesibilitySettingsVisibility(): void {
    this.displayAccessibilitySettings = !this.displayAccessibilitySettings;
    this.vardaLocalStorageWrapper.saveAccessibilitySettingsVisibility(this.displayAccessibilitySettings);
  }

  ngOnInit() {
    this.vardaLocalStorageWrapper.highContrastIsEnabled().subscribe((isEnabled) => {
      this.highContrastEnabled = isEnabled;
    });

    this.vardaLocalStorageWrapper.showAccessibilitySettings().subscribe((isEnabled) => {
      this.displayAccessibilitySettings = isEnabled;
    });
  }

}
