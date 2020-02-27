import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { Observable } from 'rxjs';

@Injectable()
export class BrowserNotSupportedGuard implements CanActivate {

  constructor(private router: Router) {
  }

  canActivate(): Observable<boolean> | Promise<boolean> | boolean {
    if (/Trident\/|MSIE/.test(window.navigator.userAgent)) {
      this.router.navigate(['/browser-not-supported'])
      return false
    }

    return true;
  }
}
