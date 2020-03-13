export const fieldsets = {
  toimipaikat: [
    {
      'id': '1',
      'title': 'Perustiedot',
      'fields': [
        {
          'key': 'nimi',
          'displayName': {
            'displayNameFi': 'Toimipaikan nimi'
          },
          'widget': 'string',
          'instructionText': {
            'instructionTextFi': 'Toimipaikan nimi'
          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Nimi on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 200,
              'errorText': {
                'errorTextFi': 'Nimi voi olla maksimissaan 200 merkkiä.'
              }
            },
            'regex': {},
            'rejectSpecialCharsNames': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja'
              }
            },
            'disabledOnEdit': {
              'acceptedValue': true
            }
          }
        },
        {
          'key': 'organisaatio_oid',
          'displayName': {
            'displayNameFi': 'OID-tunniste'
          },
          'widget': 'string',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.2'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'OID-tunniste on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 100,
              'errorText': {
                'errorTextFi': 'Maksimipituus on 100 merkkiä.'
              }
            },
            'regex': {},
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja'
              }
            }
          }
        }
      ]
    },
    {
      'id': '2',
      'title': 'Yhteystiedot',
      'fields': [
        {
          'key': 'katuosoite',
          'displayName': {
            'displayNameFi': 'Katuosoite'
          },
          'widget': 'string',
          'instructionText': {
            'instructionTextFi': 'Käytä tarvittaessa lyhenteitä.'
          },
          'placeholder': {
            'placeholderFi': 'Esimerkkikatu 12'
          },
          'styles': {
            'width': '0.7'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Katuosoite on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 100,
              'errorText': {
                'errorTextFi': 'Katuosoite voi olla maksimissaan 100 merkkiä pitkä.'
              }
            },
            'regex': {},
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja'
              }
            }
          }
        },
        {
          'key': 'postinumero',
          'displayName': {
            'displayNameFi': 'Postinumero'
          },
          'widget': 'string',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.2'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Postinumero on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 5,
              'errorText': {
                'errorTextFi': 'Postinumeron maksimipituus on 5 merkkiä.'
              }
            },
            'minlength': {
              'acceptedValue': 5,
              'errorText': {
                'errorTextFi': 'Postinumeron minimipituus on 5 merkkiä.'
              }
            },
            'regex': {
              'acceptedValue': '^\\d+$',
              'errorText': {
                'errorTextFi': 'Postinumerossa voi olla vain numeroita.'
              }
            },
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja.'
              }
            }
          }
        },
        {
          'key': 'postitoimipaikka',
          'displayName': {
            'displayNameFi': 'Postitoimipaikka'
          },
          'widget': 'string',
          'instructionText': {
            'instructionTextFi': 'Käytä tarvittaessa lyhenteitä.'
          },
          'placeholder': {
            'placeholderFi': 'Espoo'
          },
          'styles': {
            'width': '0.5'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Postitoimipaikka on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 50,
              'errorText': {
                'errorTextFi': 'Postitoimipaikan nimi voi olla maksimissaan 50 merkkiä pitkä'
              }
            },
            'regex': {},
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja'
              }
            }
          }
        },
        {
          'key': 'kunta_koodi',
          'displayName': {
            'displayNameFi': 'Kuntakoodi'
          },
          'widget': 'select',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.2'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Kuntakoodi on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 20,
              'errorText': {
                'errorTextFi': 'Kuntakoodin maksimipituus on 10 merkkiä.'
              }
            },
            'regex': {
              'acceptedValue': '^\\d+$',
              'errorText': {
                'errorTextFi': 'Kuntakoodisssa voi olla vain numeroita.'
              }
            },
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja.'
              }
            }
          }
        },
        {
          'key': 'puhelinnumero',
          'displayName': {
            'displayNameFi': 'Puhelinnumero'
          },
          'widget': 'string',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': '09123456'
          },
          'styles': {
            'width': '0.4'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Puhelinnumero on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 20,
              'errorText': {
                'errorTextFi': 'Maksimipituus on 20 merkkiä.'
              }
            },
            'regex': {
              'acceptedValue': '^([+]\\d|\\d|\\s)+$',
              'errorText': {
                'errorTextFi': 'Huom! Puhelinnumerossa voi olla numeroita, + -merkki ja välilyöntejä'
              }
            },
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja.'
              }
            }
          }
        },
        {
          'key': 'sahkopostiosoite',
          'displayName': {
            'displayNameFi': 'Sähköpostiosoite'
          },
          'widget': 'string',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': 'etunimi.sukunimi@esimerkki.fi'
          },
          'styles': {
            'width': '0.8'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Sähköpostiosoite on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 100,
              'errorText': {
                'errorTextFi': 'Maksimipituus on 100 merkkiä.'
              }
            },
            'regex': {
              'acceptedValue': '^\\w+([\\.-]?\\w+)*@\\w+([\\.-]?\\w+)*(\\.\\w{2,3})+$',
              'errorText': {
                'errorTextFi': 'Sähköpostiosoitteessasi näyttäisi olevan kirjoitusvirhe.'
              }
            },
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja.'
              }
            }
          }
        }
      ]
    },
    {
      'id': '3',
      'title': 'Lisätiedot',
      'fields': [
        {
          'key': 'toimintamuoto_koodi',
          'displayName': {
            'displayNameFi': 'Toimintamuoto'
          },
          'widget': 'select',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'options': [
            {
              'code': 'tm01',
              'displayName': {
                'displayNameFi': 'Päiväkoti'
              }
            },
            {
              'code': 'tm02',
              'displayName': {
                'displayNameFi': 'Perhepäivähoito'
              }
            },
            {
              'code': 'tm03',
              'displayName': {
                'displayNameFi': 'Ryhmäperhepäivähoito'
              }
            }
          ],
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Toimintamuoto on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 50,
              'errorText': {
                'errorTextFi': 'Maksimipituus on 50 merkkiä.'
              }
            },
            'regex': {},
            'disabledOnEdit': {
              'acceptedValue': true
            }
          }
        },
        {
          'key': 'jarjestamismuoto_koodi',
          'displayName': {
            'displayNameFi': 'Järjestämismuoto'
          },
          'widget': 'chkgroup',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'options': [
            {
              'code': 'jm01',
              'displayName': {
                'displayNameFi': 'Kunnan tai kuntayhtymän järjestämä'
              }
            },
            {
              'code': 'jm02',
              'displayName': {
                'displayNameFi': 'Kunnan tai kuntayhtymän ostopalvelu'
              }
            },
            {
              'code': 'jm03',
              'displayName': {
                'displayNameFi': 'Palvelusetelillä järjestetty'
              }
            },
            {
              'code': 'jm04',
              'displayName': {
                'displayNameFi': 'Yksityisen hoidon tuella järjestetty'
              }
            }
          ],
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Järjestämismuoto on pakollinen'
              }
            }
          }
        },
        {
          'key': 'asiointikieli_koodi',
          'displayName': {
            'displayNameFi': 'Asiointikieli'
          },
          'widget': 'selectArr',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'koodisto': 'kielikoodisto',
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Asiointikieli on pakollinen'
              }
            },
            'selectArrMustHaveOneValue': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Vähintään yksi asiointikieli pitää valita',
                'errorTextSv': ''
              }
            }
          }
        },
        {
          'key': 'kasvatusopillinen_jarjestelma_koodi',
          'displayName': {
            'displayNameFi': 'Kasvatusopillinenjärjestelmä'
          },
          'widget': 'select',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'options': [
            {
              'code': 'kj01',
              'displayName': {
                'displayNameFi': 'Steiner-pedagogiikka'
              }
            },
            {
              'code': 'kj02',
              'displayName': {
                'displayNameFi': 'Montessori-pedagogiikka'
              }
            },
            {
              'code': 'kj03',
              'displayName': {
                'displayNameFi': 'Freinet-pedagogiikka'
              }
            },
            {
              'code': 'kj04',
              'displayName': {
                'displayNameFi': 'Reggio Emilia –pedagogiikka'
              }
            },
            {
              'code': 'kj05',
              'displayName': {
                'displayNameFi': 'Freireläinen pedagogiikka'
              }
            },
            {
              'code': 'kj98',
              'displayName': {
                'displayNameFi': 'Ei painotusta'
              }
            },
            {
              'code': 'kj99',
              'displayName': {
                'displayNameFi': 'Muu'
              }
            }
          ],
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Kasvatusopillinenjärjestelmä on pakollinen'
              }
            },
            'maxlength': {
              'acceptedValue': 200,
              'errorText': {
                'errorTextFi': 'Maksimipituus on 100 merkkiä.'
              }
            },
            'regex': {},
            'rejectSpecialChars': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Erikoismerkit eivät ole sallittuja'
              }
            }
          }
        },
        {
          'key': 'varhaiskasvatuspaikat',
          'displayName': {
            'displayNameFi': 'Varhaiskasvatuspaikat'
          },
          'widget': 'string',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.2'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Varhaiskasvatuspaikat on pakollinen'
              }
            }
          }
        },
        {
          'key': 'alkamis_pvm',
          'displayName': {
            'displayNameFi': 'Alkamispäivämäärä'
          },
          'widget': 'date',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': 'pp.kk.vvvv'
          },
          'styles': {
            'width': '0.4'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Alkamispäivämäärä on pakollinen'
              }
            },
            'vardaUIDate': {
              'acceptedValue': 'dd.mm.yyyy',
              'errorText': {
                'errorTextFi': 'Alkamispäivämäärä tulee olla muodossa pp.kk.vvvv'
              }
            }
          }
        },
        {
          'key': 'paattymis_pvm',
          'displayName': {
            'displayNameFi': 'Päättymispäivämäärä (jos tiedossa)'
          },
          'instructionText': {},
          'widget': 'date',
          'placeholder': {},
          'styles': {
            'width': '0.4'
          },
          'rules': {
            'vardaUIDate': {
              'acceptedValue': 'dd.mm.yyyy',
              'errorText': {
                'errorTextFi': 'Alkamispäivämäärä tulee olla muodossa pp.kk.vvvv'
              }
            }
          }
        }
      ]
    }
  ],
  varhaiskasvatuspaatokset: [
    {
      'id': 'varhaiskasvatuspaatos_hakemusjapaatostiedot',
      'title': 'Hakemus- ja päätöstiedot',
      'fields': [
        {
          'key': 'hakemus_pvm',
          'displayName': {
            'displayNameFi': 'Hakemuspäivämäärä'
          },
          'widget': 'date',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Hakemuspäivämäärä on pakollinen'
              }
            },
            'vardaUIDate': {
              'acceptedValue': 'dd.mm.yyyy',
              'errorText': {
                'errorTextFi': 'Hakemuspäivämäärä tulee olla muodossa pp.kk.vvvv'
              }
            }
          }
        },
        {
          'key': 'alkamis_pvm',
          'displayName': {
            'displayNameFi': 'Alkamispäivämäärä'
          },
          'widget': 'date',
          'instructionText': {
            'instructionTextFi': 'asdf'
          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Alkamispäivämäärä on pakollinen'
              }
            },
            'vardaUIDate': {
              'acceptedValue': 'dd.mm.yyyy',
              'errorText': {
                'errorTextFi': 'Alkamispäivämäärä tulee olla muodossa pp.kk.vvvv'
              }
            }
          }
        },
        {
          'key': 'paattymis_pvm',
          'displayName': {
            'displayNameFi': 'Päättymispäivämäärä (jos tiedossa)'
          },
          'widget': 'date',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'rules': {
            'vardaUIDate': {
              'acceptedValue': 'dd.mm.yyyy',
              'errorText': {
                'errorTextFi': 'Päättymispäivämäärä tulee olla muodossa pp.kk.vvvv'
              }
            }
          }
        }
      ]
    },
    {
      'id': 'varhaiskasvatuspaatos_jarjestamismuoto',
      'title': 'Järjestämismuoto',
      'fields': [
        {
          'key': 'jarjestamismuoto_koodi',
          'displayName': {
            'displayNameFi': 'Järjestämismuoto'
          },
          'widget': 'select',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'options': [
            {
              'code': 'jm01',
              'displayName': {
                'displayNameFi': 'Kunnan tai kuntayhtymän järjestämä'
              }
            },
            {
              'code': 'jm02',
              'displayName': {
                'displayNameFi': 'Kunnan tai kuntayhtymän ostopalvelu'
              }
            },
            {
              'code': 'jm03',
              'displayName': {
                'displayNameFi': 'Palvelusetelillä järjestetty'
              }
            },
            {
              'code': 'jm04',
              'displayName': {
                'displayNameFi': 'Yksityisen hoidon tuella järjestetty'
              }
            }
          ],
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Järjestämismuoto on pakollinen'
              }
            },
            'disabledOnEdit': {
              'acceptedValue': true
            }
          }
        }
      ]
    },
    {
      'id': 'varhaiskasvatuspaatos_varhaiskasvatusaika',
      'title': 'Varhaiskasvatusaika',
      'fields': [
        {
          'key': 'tuntimaara_viikossa',
          'displayName': {
            'displayNameFi': 'Tuntimäärä viikossa'
          },
          'widget': 'string',
          'instructionText': {
            'instructionTextFi': 'Tuntimäärä viikossa'
          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.4'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Tuntimäärä viikossa on pakollinen'
              }
            },
            'disabledOnEdit': {
              'acceptedValue': true
            }
          }
        },
        {
          'key': 'vuorohoito_kytkin',
          'displayName': {
            'displayNameFi': 'Vuorohoito'
          },
          'widget': 'booleanradio',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.4'
          },
          'rules': {
            'dependentFields': {
              'paivittainen_vaka_kytkin': {
                'notAllowedIfKeyHasBooleanValue': {
                  'vuorohoito_kytkin': true
                }
              },
              'kokopaivainen_vaka_kytkin': {
                'notAllowedIfKeyHasBooleanValue': {
                  'vuorohoito_kytkin': true
                }
              }
            }
          }
        },
        {
          'key': 'paivittainen_vaka_kytkin',
          'displayName': {
            'displayNameFi': 'Päivittäinen varhaiskasvatus'
          },
          'widget': 'checkbox',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.4'
          },
          'rules': {}
        },
        {
          'key': 'kokopaivainen_vaka_kytkin',
          'displayName': {
            'displayNameFi': 'Kokopäiväinen varhaiskasvatus'
          },
          'widget': 'checkbox',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.4'
          },
          'rules': {}
        }
      ]
    }
  ],
  esiopetussuoritukset: [
    {
      'id': 'esiopetussuoritus_perustiedot',
      'title': 'Esiopetussuoritukset tiedot',
      'fields': [
        {
          'key': 'e_perusteviittaus',
          'displayName': {
            'displayNameFi': 'ePerusteviittaus'
          },
          'widget': 'string',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.6'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'ePerusteviittaus on pakollinen'
              }
            }
          }
        },
        {
          'key': 'suorituskieli_koodi',
          'displayName': {
            'displayNameFi': 'Suorituskieli'
          },
          'widget': 'autocompleteone',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.6'
          },
          'koodisto': 'kielikoodisto',
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Suorituskieli on pakollinen'
              }
            }
          }
        },
        {
          'key': 'muut_suorituskielet_koodi',
          'displayName': {
            'displayNameFi': 'Muut suorituskielet'
          },
          'widget': 'autocompletemany',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.6'
          },
          'koodisto': 'kielikoodisto',
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Muut suorituskielet on pakollinen'
              }
            }
          }
        },
        {
          'key': 'tutkinto_koodi',
          'displayName': {
            'displayNameFi': 'Tutkintokoodi'
          },
          'widget': 'string',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.6'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Tutkintokoodi on pakollinen'
              }
            }
          }
        },
        {
          'key': 'kuvaus_esiopetuksesta',
          'displayName': {
            'displayNameFi': 'Kuvaus esiopetuksesta'
          },
          'widget': 'textarea',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {},
          'rules': {}
        },
        {
          'key': 'tutkinnon_myontaja',
          'displayName': {
            'displayNameFi': 'Tutkinnon myöntäjä'
          },
          'widget': 'string',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.6'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Tutkinnon myöntäjä on pakollinen'
              }
            }
          }
        },
        {
          'key': 'tutkinnon_valmistumis_pvm',
          'displayName': {
            'displayNameFi': 'Tutkinnon valmistumispäivämäärä'
          },
          'widget': 'date',
          'instructionText': {},
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.8'
          },
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Tutkinnon valmistumispäivämäärä on pakollinen'
              }
            },
            'vardaUIDate': {
              'acceptedValue': 'dd.mm.yyyy',
              'errorText': {
                'errorTextFi': 'Tutkinnon valmistumispäivämäärä tulee olla muodossa pp.kk.vvvv'
              }
            }
          }
        },
        {
          'key': 'kielikylpykielet_koodi',
          'displayName': {
            'displayNameFi': 'Kielikylpykielet'
          },
          'widget': 'autocompletemany',
          'instructionText': {

          },
          'placeholder': {
            'placeholderFi': ''
          },
          'styles': {
            'width': '0.6'
          },
          'koodisto': 'kielikoodisto',
          'rules': {
            'required': {
              'acceptedValue': true,
              'errorText': {
                'errorTextFi': 'Kielikylpykielet on pakollinen'
              }
            }
          }
        }
      ]
    }
  ]
};
