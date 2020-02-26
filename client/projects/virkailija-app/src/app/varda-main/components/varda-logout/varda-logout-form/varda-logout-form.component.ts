import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-varda-logout-form',
  templateUrl: './varda-logout-form.component.html',
  styleUrls: ['./varda-logout-form.component.css']
})
export class VardaLogoutFormComponent implements OnInit {

  constructor(private router: Router) { }

  navigateToLogin(event: any): void {
    event.preventDefault();
    window.open(`/varda/login`, '_self');
  }

  ngOnInit() {
  }

}
