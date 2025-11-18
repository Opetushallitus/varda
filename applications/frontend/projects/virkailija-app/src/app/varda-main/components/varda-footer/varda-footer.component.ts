import { Component, OnInit } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaAccessibilityService } from '../../../core/services/varda-accessibility.service';

@Component({
  selector: 'app-varda-footer',
  templateUrl: './varda-footer.component.html',
  styleUrls: ['./varda-footer.component.css']
})
export class VardaFooterComponent implements OnInit {
  i18n = VirkailijaTranslations;
  displayAccessibilitySettings: boolean;

  constructor(private accessibilityService: VardaAccessibilityService) {
    this.displayAccessibilitySettings = true;
  }

  toggleAccesibilitySettingsVisibility(): void {
    this.displayAccessibilitySettings = !this.displayAccessibilitySettings;
    this.accessibilityService.saveAccessibilitySettingsVisibility(this.displayAccessibilitySettings);
  }

  ngOnInit() {
    this.accessibilityService.showAccessibilitySettings().subscribe((isEnabled) => {
      this.displayAccessibilitySettings = isEnabled;
    });
  }

}
