import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { environment } from 'projects/huoltaja-app/src/environments/environment';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
  standalone: false
})
export class LoginComponent implements OnInit {
  i18n = HuoltajaTranslations;
  loginURL = `${environment.huoltajaBackendUrl}/accounts/huoltaja-login?next=/varda/`;

  ngOnInit(): void {
    window.location.href = this.loginURL;
  }
}
