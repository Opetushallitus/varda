import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-varda-logout',
  templateUrl: './varda-logout.component.html',
  styleUrls: ['./varda-logout.component.css']
})
export class VardaLogoutComponent implements OnInit {

  constructor(private titleService: Title) { }

  ngOnInit() {
    this.titleService.setTitle(`Varda - Uloskirjautuminen`);
  }

}
