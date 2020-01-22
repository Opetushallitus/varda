import { Component, OnInit, AfterViewInit} from '@angular/core';
import { AuthService } from '../../../../core/auth/auth.service';
import { Router} from '@angular/router';
import {environment} from '../../../../../environments/environment';
import {LoginService} from 'varda-shared';

@Component({
  selector: 'app-varda-login-form',
  templateUrl: './varda-login-form.component.html',
  styleUrls: ['./varda-login-form.component.css']
})
export class VardaLoginFormComponent implements OnInit, AfterViewInit {

  next = encodeURIComponent(environment.vardaFrontendUrl + '/');
  vardaBackendLoginUrl = `${environment.vardaAppUrl}/accounts/login?next=${this.next}`;
  showLogOutMsg = false;

  constructor(
    private authService: AuthService,
    private loginService: LoginService,
    private router: Router) {
      this.loginService.isLoggedOut().subscribe((isLoggedOut: boolean) => {
        this.showLogOutMsg = isLoggedOut;
      });
  }

  navigateToVardaLogin(): void {
    window.location.href = this.vardaBackendLoginUrl;
  }

  ngAfterViewInit() {}

  ngOnInit() {
    if (this.loginService.isValidApiToken()) {
      this.router.navigate(['/']);
    }
  }

}
