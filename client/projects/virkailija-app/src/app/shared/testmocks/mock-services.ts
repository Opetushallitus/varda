import { of, Observable } from 'rxjs';
import { toimipaikatStub } from './toimipaikat-stub';
import { varhaiskasvatussuhteetStub } from './varhaiskasvatussuhteet-stub';
import { varhaiskasvatuspaatoksetStub } from './varhaiskasvatuspaatokset-stub';
import { lapsetStub } from './lapset-stub';
import {lapsetByToimipaikkaStub} from './lapset-by-toimipaikka-stub';

export const vardaApiWrapperServiceStub = {
    getVakaJarjestajaById() {
        const vakajarjestaja = {url: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/vakajarjestajat/2/'};
        return of(vakajarjestaja);
    },
    getVakajarjestaForLoggedInUser() {
        const vakajarjestaja = {url: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/vakajarjestajat/2/'};
        return of(vakajarjestaja);
    },
    getAllLapsetForToimipaikka() {
      return of(lapsetByToimipaikkaStub);
    },
    getToimipaikatForVakajarjestaja() {
        const toimipaikat = toimipaikatStub;
        return of(toimipaikat);
    },
    getAllToimipaikatForVakajarjestaja() {
        const toimipaikat = toimipaikatStub;
        return of(toimipaikat);
    },
    getVarhaiskasvatussuhteet() {
        return of(varhaiskasvatussuhteetStub);
    },
    getVarhaiskasvatussuhteetByToimipaikka(id: string) {
        const varhaiskasvatussuhteet = varhaiskasvatussuhteetStub;
        return of(varhaiskasvatussuhteet);
    },
    getLapsetByVarhaiskasvatussuhteet(varhaiskasvatussuhteet: any) {
        const lapset = lapsetStub;
        return of(lapset);
    },
    getCreateLapsiFieldSets() {
        return of({0: {
            fieldsets: [
                {id: 'aaa', title: 'aaa', fields: [{key: 'aaa-field'}, {key: 'aaa-field2'}]}
            ]
        },
        1: {
            fieldsets: [
                {id: 'varhaiskasvatuspaatos_hakemusjapaatostiedot', title: 'Hakemus- ja päätöstiedot', fields: [{key: 'hakemus_pvm'}]},
                {id: 'varhaiskasvatuspaatos_jarjestamismuoto', title: 'Järjestämismuoto', fields: [{key: 'jarjestamismuoto_koodi'}]},
                {id: 'varhaiskasvatuspaatos_varhaiskasvatusaika', title: 'Varhaiskasvatusaika', fields: [{key: 'vuorohoito_kytkin'},
                {key: 'tuntimaara_viikossa'}]}
            ]
        }});
    },
    getEntityReferenceByEndpoint() {
        return of(lapsetStub[0]);
    },
    getVarhaiskasvatussuhteetByLapsi(lapsiId: string) {
        return of(varhaiskasvatussuhteetStub);
    },
    getVarhaiskasvatuspaatoksetByLapsi(lapsiId: string) {
        return of(varhaiskasvatuspaatoksetStub);
    },
    deleteVarhaiskasvatuspaatos(id: string) {
        return of({});
    },
    createNewLapsi(henkilo: any, toimipaikka: any, suhteet: any, data: any) {
        return of({});
    }
};
