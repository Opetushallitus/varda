import {Component, EventEmitter, Input, Output} from "@angular/core";
import {VardaToimipaikkaMinimalDto} from "../../../../../utilities/models/dto/varda-toimipaikka-dto.model";
import {VirkailijaTranslations} from "../../../../../../assets/i18n/virkailija-translations.enum";

@Component({
  selector: 'app-varda-toimipaikka-list',
  templateUrl: './varda-toimipaikka-list.component.html',
  styleUrls: ['./varda-toimipaikka-list.component.css', '../../varda-main-frame.component.css'],
  standalone: false
})
export class VardaToimipaikkaListComponent {
  @Input() toimipaikkaList: Array<VardaToimipaikkaMinimalDto>;
  @Output() updateToimipaikkaSelection = new EventEmitter<VardaToimipaikkaMinimalDto>(true);

  protected readonly i18n = VirkailijaTranslations;

  clickItem(toimipaikka: VardaToimipaikkaMinimalDto) {
    this.updateToimipaikkaSelection.emit(toimipaikka);
  }
}
