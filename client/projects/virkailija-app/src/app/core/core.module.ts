import { NgModule, Optional, SkipSelf } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../shared/shared.module';
import { VardaApiService } from './services/varda-api.service';
import { VardaAccessibilityService } from './services/varda-accessibility.service';
import { VardaFormService } from './services/varda-form.service';
import { VardaApiWrapperService } from './services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from './services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaApiService } from './services/varda-vakajarjestaja-api.service';
import { VardaUtilityService } from './services/varda-utility.service';
import { VardaModalService } from './services/varda-modal.service';
import { VardaErrorMessageService } from './services/varda-error-message.service';
import { VardaDomService } from './services/varda-dom.service';
import { VardaHenkilostoApiService } from './services/varda-henkilosto.service';
import { VardaLapsiService } from './services/varda-lapsi.service';
import { VardaRaportitService } from './services/varda-raportit.service';
import { VardaSnackBarService } from './services/varda-snackbar.service';
import { VardaPaosApiService } from './services/varda-paos-api.service';
import { VardaKoosteApiService } from './services/varda-kooste-api.service';

@NgModule({
  imports: [
    CommonModule,
    SharedModule
  ],
  providers: [
    VardaApiService,
    VardaAccessibilityService,
    VardaFormService,
    VardaApiWrapperService,
    VardaVakajarjestajaService,
    VardaVakajarjestajaApiService,
    VardaUtilityService,
    VardaModalService,
    VardaErrorMessageService,
    VardaDomService,
    VardaHenkilostoApiService,
    VardaLapsiService,
    VardaRaportitService,
    VardaPaosApiService,
    VardaSnackBarService,
    VardaKoosteApiService,
  ]
})
export class CoreModule {
  constructor(@Optional() @SkipSelf() parentModule: CoreModule) {
    if (parentModule) {
      throw new Error(
        'CoreModule is already loaded. Import it in the AppModule only');
    }
  }
}
