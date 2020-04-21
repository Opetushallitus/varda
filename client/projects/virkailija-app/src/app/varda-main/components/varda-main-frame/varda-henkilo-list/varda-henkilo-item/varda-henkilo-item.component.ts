import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { VardaExtendedHenkiloModel, VardaLapsiDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';

@Component({
  selector: 'app-varda-henkilo-item',
  templateUrl: './varda-henkilo-item.component.html',
  styleUrls: ['./varda-henkilo-item.component.css']
})
export class VardaHenkiloListItemComponent implements OnInit {

  @Input() henkiloItem: VardaExtendedHenkiloModel;
  @Input() activeHenkiloItemId: string;
  @Output() editHenkiloItem: EventEmitter<any> = new EventEmitter();

  constructor(private vardaVakajarjestajaService: VardaVakajarjestajaService) { }

  editHenkilo(): void {
    setTimeout(() => {
      this.henkiloItem.isNew = false;
    }, 500);
    const henkilo = this.henkiloItem.henkilo;
    this.editHenkiloItem.emit(henkilo);
  }

  ngOnInit() {}

  getVakaJarjestajaText(lapsi: VardaLapsiDTO): string {
    return this.vardaVakajarjestajaService.getVakaJarjestajaTextForLists(lapsi);
  }
}
