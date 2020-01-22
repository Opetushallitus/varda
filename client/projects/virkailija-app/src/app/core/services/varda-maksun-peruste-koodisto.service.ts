import {Injectable} from '@angular/core';
import {VardaApiService} from './varda-api.service';
import {LangChangeEvent, TranslateService} from '@ngx-translate/core';
import {EMPTY, Observable} from 'rxjs';
import {VardaKoodistoDto, VardaKoodistoMetadataDto} from '../../utilities/models/dto/varda-koodisto-dto.model';
import {map} from 'rxjs/operators';
import * as moment from 'moment';

@Injectable({
  providedIn: 'root'
})
export class VardaMaksunPerusteKoodistoService {
  maksunPerusteKoodit: Array<VardaKoodistoDto>;
  currentLang: string;
  isLoading: boolean;

  constructor(private vardaApiService: VardaApiService,
              private translateService: TranslateService) {
    this.isLoading = false;
    this.maksunPerusteKoodit = [];
    this.currentLang = this.translateService.currentLang;
    this.translateService.onLangChange.subscribe((event: LangChangeEvent) => {
      this.currentLang = event.lang;
    });
  }

  initialise(): Observable<boolean> {
    if (!!this.maksunPerusteKoodit.length || this.isLoading) {
      return EMPTY;
    }
    return new Observable((observer) => {
      this.isLoading = true;
      this.vardaApiService.getMaksunPerustekoodisto()
        .pipe(map(this.sortKoodistoOptions.bind(this)))
        .pipe(map(this.exclude.bind(this)))
        .subscribe((maksunPerusteKoodit: Array<VardaKoodistoDto>) => {
          this.isLoading = false;
          this.maksunPerusteKoodit = maksunPerusteKoodit;
          observer.next(true);
          observer.complete();
        }, error => {
          console.error(error);
          return observer.error({koodistoUnavailable: true});
        });
    });
  }

  private sortKoodistoOptions(maksunPerusteKoodit: Array<VardaKoodistoDto>): Array<VardaKoodistoDto> {
    return maksunPerusteKoodit.sort((a: VardaKoodistoDto, b: VardaKoodistoDto) => {
      const metadataFiA = this.getKoodistoOptionMetadataByLang(a.metadata, this.currentLang);
      const metadataFiB = this.getKoodistoOptionMetadataByLang(b.metadata, this.currentLang);

      const nameA = metadataFiA.nimi.toUpperCase();
      const nameB = metadataFiB.nimi.toUpperCase();

      return nameA.localeCompare(nameB);
    });
  }

  getKoodistoOptionMetadataByLang(koodistoOptionMetadata: Array<VardaKoodistoMetadataDto>,
                                          language: string): VardaKoodistoMetadataDto {
    return koodistoOptionMetadata.find((metadataObj) => {
      return metadataObj.kieli.toUpperCase() === language.toUpperCase();
    });
  }

  private exclude(maksunPerusteKoodit: Array<VardaKoodistoDto>): Array<VardaKoodistoDto> {
    return maksunPerusteKoodit.filter(maksunPerusteKoodi => {
      const voimassaLoppuPvm = maksunPerusteKoodi.voimassaLoppuPvm;
      return !voimassaLoppuPvm || moment().isBefore(voimassaLoppuPvm);
    });
  }

  getKoodistoOptions(): Array<VardaKoodistoDto> {
    return this.maksunPerusteKoodit;
  }
}
