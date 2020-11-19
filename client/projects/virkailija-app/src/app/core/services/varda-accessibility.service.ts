import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject } from 'rxjs';
import { VardaCookieEnum } from '../../utilities/models/enums/varda-cookie.enum';

@Injectable()
export class VardaAccessibilityService {
  private fontSize: BehaviorSubject<number>;
  private highContrastEnabled: BehaviorSubject<boolean>;
  private displayAccessibilitySettings: BehaviorSubject<boolean>;

  constructor() {
    this.fontSize = this.initFontSizeObservable();
    this.highContrastEnabled = this.initHighContrastObservable();
    this.displayAccessibilitySettings = this.initAccessibilitySettingsObservable();
  }

  showAccessibilitySettings(): Observable<boolean> {
    return this.displayAccessibilitySettings.asObservable();
  }

  highContrastIsEnabled(): Observable<boolean> {
    return this.highContrastEnabled.asObservable();
  }

  getFontSize(): Observable<number> {
    return this.fontSize.asObservable();
  }

  saveFontSize(fontSize: number): void {
    localStorage.setItem(VardaCookieEnum.font_size, fontSize.toString());
    this.fontSize.next(fontSize);
  }

  saveContrastSelection(highContrastEnabled: boolean): void {
    localStorage.setItem(VardaCookieEnum.high_contrast, highContrastEnabled.toString());
    this.highContrastEnabled.next(highContrastEnabled);
  }

  saveAccessibilitySettingsVisibility(displayAccessibilitySettings: boolean): void {
    localStorage.setItem(VardaCookieEnum.display_accessibility_settings, displayAccessibilitySettings.toString());
    this.displayAccessibilitySettings.next(displayAccessibilitySettings);
  }

  initFontSizeObservable(): BehaviorSubject<number> {
    const fontSize = parseInt(localStorage.getItem(VardaCookieEnum.font_size));
    const rv = isNaN(fontSize) ? 16 : fontSize;
    return new BehaviorSubject(rv);
  }

  initHighContrastObservable(): BehaviorSubject<boolean> {
    const highContrastEnabled = localStorage.getItem(VardaCookieEnum.high_contrast);
    const rv = highContrastEnabled === 'true' ? true : false;
    return new BehaviorSubject(rv);
  }

  initAccessibilitySettingsObservable(): BehaviorSubject<boolean> {
    const accessibilitySettingsVisible = localStorage.getItem(VardaCookieEnum.display_accessibility_settings);
    const rv = accessibilitySettingsVisible === 'true' ? true : false;
    return new BehaviorSubject(rv);
  }

}
