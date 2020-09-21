import { Component, OnInit } from '@angular/core';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-huoltaja-dashboard',
  templateUrl: './huoltaja-dashboard.component.html',
  styleUrls: ['./huoltaja-dashboard.component.css']
})
export class HuoltajaDashboardComponent  {
  i18n = HuoltajaTranslations;



}
