import { Injectable } from '@angular/core';
import {Observable, BehaviorSubject } from 'rxjs';

@Injectable()
export class VardaLocalstorageWrapperService {

  private highContrastEnabled: BehaviorSubject<boolean>;
  private displayAccessibilitySettings: BehaviorSubject<boolean>;

  constructor() {
    this.highContrastEnabled = this.initHighContrastObservable();
    this.displayAccessibilitySettings = this.initAccessibilitySettingsObservable();
  }

  showAccessibilitySettings(): Observable<boolean> {
    return this.displayAccessibilitySettings.asObservable();
  }

  highContrastIsEnabled(): Observable<boolean> {
    return this.highContrastEnabled.asObservable();
  }

  saveToLocalStorage(key: string, data: any): void {
    localStorage.setItem(key, data);
  }

  getFromLocalStorage(key: string): any {
    return localStorage.getItem(key);
  }

  saveContrastSelection(highContrastEnabled: boolean): void {
    localStorage.setItem('ui.highcontrast', highContrastEnabled.toString());
    this.highContrastEnabled.next(highContrastEnabled);
  }

  saveAccessibilitySettingsVisibility(displayAccessibilitySettings: boolean): void {
    localStorage.setItem('ui.displayaccessibilitysettings', displayAccessibilitySettings.toString());
    this.displayAccessibilitySettings.next(displayAccessibilitySettings);
  }

  initHighContrastObservable(): BehaviorSubject<boolean> {
    const highContrastEnabled = this.getFromLocalStorage('ui.highcontrast');
    const rv = highContrastEnabled === 'true' ? true : false;
    return new BehaviorSubject(rv);
  }

  initAccessibilitySettingsObservable(): BehaviorSubject<boolean> {
    const accessibilitySettingsVisible = this.getFromLocalStorage('ui.displayaccessibilitysettings');
    const rv = accessibilitySettingsVisible === 'true' ? true : false;
    return new BehaviorSubject(rv);
  }

  fakeAsyncCall(data: any): Observable<any> {
    return new Observable((observer) => {
      setTimeout(() => {
        observer.next(data);
        observer.complete();
      }, 2000);
    });
  }
}
