import { Component, OnInit, Input } from '@angular/core';
import { AuthService } from '../../../core/auth/auth.service';
import {LoginService} from 'varda-shared';

@Component({
  selector: 'app-varda-info-modal',
  templateUrl: './varda-info-modal.component.html',
  styleUrls: ['./varda-info-modal.component.css']
})
export class VardaInfoModalComponent implements OnInit {

  @Input() modalTitle: string;
  @Input() modalType: string;
  @Input() isLg: boolean;

  userUsername: string;
  userEmail: string;

  constructor(private loginService: LoginService) { }

  ngOnInit() {
    setTimeout(() => {
      this.userUsername = this.loginService.getUsername();
      this.userEmail = this.loginService.getUserEmail();
    }, 2000);
  }

}
