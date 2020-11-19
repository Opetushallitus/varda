import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { LoginErrorType } from 'projects/virkailija-app/src/app/core/auth/auth.guard';

@Component({
  selector: 'app-varda-login-failed',
  templateUrl: './login-failed.component.html',
  styleUrls: ['../login-page.component.css', './login-failed.component.css']
})
export class LoginFailedComponent implements OnInit {
  errorType = LoginErrorType;
  opintopolkuName = window.location.host;
  fragment: LoginErrorType = this.errorType.unknown;

  constructor(private route: ActivatedRoute) {
    this.route.fragment.subscribe((fragment: LoginErrorType) =>
      Object.values(LoginErrorType).includes(fragment) ? this.fragment = fragment : this.fragment
    );
  }

  ngOnInit(): void {
  }

}
