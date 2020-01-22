import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-varda-login',
  templateUrl: './varda-login.component.html',
  styleUrls: ['./varda-login.component.css']
})
export class VardaLoginComponent implements OnInit {

  constructor(private titleService: Title, private translateService: TranslateService) {}

  ngOnInit() {
    this.translateService.get('label.varda-login').subscribe((translation) => {
      this.titleService.setTitle(translation);
    });
  }
}
