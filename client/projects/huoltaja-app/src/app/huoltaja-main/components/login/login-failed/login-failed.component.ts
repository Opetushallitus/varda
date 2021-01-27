import { Component } from '@angular/core';

@Component({
  selector: 'app-login-failed',
  templateUrl: './login-failed.component.html',
  styleUrls: ['./login-failed.component.css', '../login.component.css']
})
export class LoginFailedComponent {
  originLink: string = window.origin;
  constructor() { }

}
