import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
    selector: 'app-browser-not-supported',
    templateUrl: './browser-not-supported.component.html',
    styleUrls: ['./browser-not-supported.component.css'],
    standalone: false
})
export class BrowserNotSupportedComponent {
  constructor(private router: Router) {
    if (!/Trident\/|MSIE/.test(window.navigator.userAgent)) {
      this.router.navigate(['/']);
    }
  }
}
