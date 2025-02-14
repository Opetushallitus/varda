import { Component, Input, OnInit } from '@angular/core';
import { TaydennyskoulutusDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/tyontekija-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { BehaviorSubject } from 'rxjs';
import { KoodistoEnum, VardaKoodistoService } from 'varda-shared';

@Component({
  selector: 'app-taydennyskoulutus',
  templateUrl: './taydennyskoulutus.component.html',
  styleUrls: ['./taydennyskoulutus.component.css']
})
export class TaydennyskoulutusComponent implements OnInit {
  @Input() taydennyskoulutus: TaydennyskoulutusDTO;
  i18n = HuoltajaTranslations;
  koodistoEnum = KoodistoEnum;
  tehtavanimikeList = new BehaviorSubject<string>(null);
  expanded: boolean;


  constructor(private koodistoService: VardaKoodistoService) { }

  ngOnInit(): void {
    const nimikkeet = [];
    this.taydennyskoulutus.tehtavanimike_koodi_list.map(koodi =>
      this.koodistoService.getCodeValueFromKoodisto(KoodistoEnum.tehtavanimike, koodi).subscribe(codeValue => {
        nimikkeet.push(codeValue.name);
        this.tehtavanimikeList.next(nimikkeet.join(', '));
      })
    );
  }

  togglePanel(expand: boolean) {
    this.expanded = expand;
  }
}
