import { Component, OnInit } from '@angular/core';

import { HuoltajaFrontpageDto } from '../../../utilities/models/dto/huoltaja-frontpage-dto';
import {HuoltajaApiService} from '../../../services/huoltaja-api.service';
import {LoginService} from 'varda-shared';

@Component({
  selector: 'app-huoltaja-frontpage',
  templateUrl: './huoltaja-frontpage.component.html',
  styleUrls: ['./huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageComponent implements OnInit {

  frontpageDto: HuoltajaFrontpageDto;

  constructor(private apiService: HuoltajaApiService,
              private loginService: LoginService) {}

  initialize() {
    this.frontpageDto = {
      lapsi: {
        henkilo_oid: '1.2.3.00000004',
        henkilotunnus: '110117A1526',
        etunimet: 'Onni Matias',
        kutsumanimi: 'Onni',
        sukunimi: 'Kumpulainen',
        aidinkieli: 'suomi',
        syntymaaika: '2017-01-11',
        sukupuoli: 'Mies',
        kotikunta: 'Espoo',
        postinumero: '02120',
        postitoimipaikka: 'Espoo',
        toggle_expanded: false
      },
      voimassa_useita_vakapaatoksia: true,
      toimipaikat: [
        {
          nimi: 'Päiväkoti Mustikka, Jyväskylä',
          vakasuhteet: [
            {
              vakapaatos_voimassa: true,
              alkamis_pvm: '2019-01-01',
              vakapaatokset: [
                {
                  alkamis_pvm: '2019-01-01',
                  hakemus_pvm: '2018-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                }
              ]
            }
          ]
        },
        {
          nimi: 'Päiväkoti Kaarnalaiva, Hyvinkää',
          vakasuhteet: [
            {
              vakapaatos_voimassa: true,
              alkamis_pvm: '2018-01-01',
              paattymis_pvm: '2018-12-31',
              vakapaatokset: [
                {
                  alkamis_pvm: '2018-01-01',
                  paattymis_pvm: '2018-06-30',
                  hakemus_pvm: '2017-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                },
                {
                  alkamis_pvm: '2018-07-01',
                  paattymis_pvm: '2018-12-31',
                  hakemus_pvm: '2017-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                }
              ]
            }
          ]
        },
        {
          nimi: 'Päiväkoti Mansikka, Asikkala',
          vakasuhteet: [
            {
              vakapaatos_voimassa: false,
              alkamis_pvm: '2017-01-01',
              paattymis_pvm: '2017-12-20',
              vakapaatokset: [
                {
                  alkamis_pvm: '2017-01-01',
                  paattymis_pvm: '2017-03-31',
                  hakemus_pvm: '2016-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                },
                {
                  alkamis_pvm: '2017-04-01',
                  paattymis_pvm: '2017-06-30',
                  hakemus_pvm: '2016-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                },
                {
                  alkamis_pvm: '2017-07-01',
                  paattymis_pvm: '2017-12-20',
                  hakemus_pvm: '2016-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                }
              ]
            }
          ]
        },
        {
          nimi: 'Päiväkoti Puolukka, Tampere',
          vakasuhteet: [
            {
              vakapaatos_voimassa: false,
              alkamis_pvm: '2016-07-01',
              paattymis_pvm: '2016-12-31',
              vakapaatokset: [
                {
                  alkamis_pvm: '2016-07-01',
                  paattymis_pvm: '2016-12-31',
                  hakemus_pvm: '2015-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                }
              ]
            },
            {
              vakapaatos_voimassa: false,
              alkamis_pvm: '2016-01-01',
              paattymis_pvm: '2016-06-30',
              vakapaatokset: [
                {
                  alkamis_pvm: '2016-01-01',
                  paattymis_pvm: '2016-06-30',
                  hakemus_pvm: '2015-01-01',
                  toimipaikkaan_sijoittuminen: 'Espoo',
                  tuntimaara_viikossa: 40,
                  jarjestamismuoto: 'Kunnan tai kuntayhtymän järjestämä',
                  paivittainen_vaka_kytkin: true,
                  kokopaivainen_vaka_kytkin: true,
                  vuorohoito_kytkin: false,
                  osaviikkoinen_vaka_kytkin: false,
                  osapaivainen_vaka_kytkin: false,
                  toggle_expanded: false
                }
              ]
            }
          ]
        },
      ]
    };
  }

  ngOnInit() {
    this.initialize();
  }
}
