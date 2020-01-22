import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { VardaExtendedHenkiloModel } from '../../../utilities/models';

@Component({
  selector: 'app-varda-henkilo-item',
  templateUrl: './varda-henkilo-item.component.html',
  styleUrls: ['./varda-henkilo-item.component.css']
})
export class VardaHenkiloItemComponent implements OnInit {

  @Input() henkiloItem: VardaExtendedHenkiloModel;
  @Input() activeHenkiloItemId: string;
  @Output() editHenkiloItem: EventEmitter<any> = new EventEmitter();

  constructor() { }

  editHenkilo(): void {
    setTimeout(() => {
      this.henkiloItem.isNew = false;
    }, 500);
    const henkilo = this.henkiloItem.henkilo;
    this.editHenkiloItem.emit(henkilo);
  }

  ngOnInit() {}
}
