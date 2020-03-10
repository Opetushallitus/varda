import { browser, by, element, protractor } from 'protractor';

export class ToimipaikkaFormPage {

    testText = 'varda e2e user';

    // Toimipaikka form inputs
    nimi = element(by.id('nimi0'));
    kayntiosoite = element(by.id('kayntiosoite1'));
    kayntiosoite_postinumero = element(by.id('kayntiosoite_postinumero1'));
    kayntiosoite_postitoimipaikka = element(by.id('kayntiosoite_postitoimipaikka1'));
    postiosoite = element(by.id('postiosoite1'));
    postinumero = element(by.id('postinumero1'));
    postitoimipaikka = element(by.id('postitoimipaikka1'));
    kunta_koodi = element(by.id('kunta_koodi1'));
    puhelinnumero = element(by.id('puhelinnumero1'));
    sahkopostiosoite = element(by.id('sahkopostiosoite1'));
    toimintamuoto_koodi = element(by.id('toimintamuoto_koodi2'));
    jarjestamismuoto_koodi_jm01 = element.all(by.css('.mat-checkbox-label')).get(0);
    jarjestamismuoto_koodi_jm02 = element.all(by.css('.mat-checkbox-label')).get(1);
    jarjestamismuoto_koodi_jm03 = element.all(by.css('.mat-checkbox-label')).get(2);
    jarjestamismuoto_koodi_jm04 = element.all(by.css('.mat-checkbox-label')).get(3);
    asiointikieli_koodi = element.all(by.css('select')).get(4);
    kasvatusopillinen_jarjestelma_koodi = element(by.id('kasvatusopillinen_jarjestelma_koodi2'));
    varhaiskasvatuspaikat = element(by.id('varhaiskasvatuspaikat2'));
    alkamis_pvm = element(by.css('my-date-picker[id=alkamis_pvmtoimipaikka2]')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    paattymis_pvm = element(by.css('my-date-picker[id=paattymis_pvmtoimipaikka2]')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();

    // Toimipaikka form buttons
    saveToimipaikkaBtn = element(by.id('toimipaikkaFormSaveToimipaikkaBtn'));

    // Toimipaikka form others
    dialogTitleLabel = element(by.id('vardaModalTitleLabeltoimipaikkaModal'));
    tallennusOnnistuiAlert = element(by.css('div[class="alert alert-success varda-form-main-feedback ng-star-inserted"]'));
    lapsiTallennusOnnistuiAlert = element(by.css('div[class="alert alert-success varda-form-main-feedback ng-star-inserted"]'));
    lapsiSuccessModal = element(by.id('lapsiSuccessModal'));

    // Lisää lapsi toimipaikkaan form inputs
    henkilotunnus = element(by.id('henkiloFormSsnOrOid'));
    etunimet = element(by.id('henkiloFormFirstnames'));
    kutsumanimi = element(by.id('henkiloFormNickname'));
    sukunimi = element(by.id('henkiloFormLastname'));
    vaka_alkamis_pvm = element(by.id('alkamis_pvmvarhaiskasvatussuhde_perustiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    vaka_paattymis_pvm = element(by.id('paattymis_pvmvarhaiskasvatussuhde_perustiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    hakemus_pvm = element(by.id('hakemus_pvmvarhaiskasvatuspaatos_hakemusjapaatostiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    hakemus_alkamis_pvm = element(by.id('alkamis_pvmvarhaiskasvatuspaatos_hakemusjapaatostiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    hakemus_paattymis_pvm = element(by.id('paattymis_pvmvarhaiskasvatuspaatos_hakemusjapaatostiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    jarjestamismuoto_koodi = element(by.id('jarjestamismuoto_koodi0'));
    tuntimaara_viikossa = element(by.id('tuntimaara_viikossa0'));
    paivittainen_vaka = element(by.css('mat-checkbox[name=paivittainen_vaka_kytkin]')).all(by.css('label')).first();
    kokopaivainen_vaka = element(by.css('mat-checkbox[name=kokopaivainen_vaka_kytkin]')).all(by.css('label')).first();

    // Lisää lapsi toimipaikkaan form buttons
    lisaaLapsiBtn = element(by.buttonText('Lisää'));
    editLapsiBtn = element(by.css('p[class="varda-henkilo-item-entry"]'));

    // Muokkaa lapsi form inputs
    vakaPaatoksetDropdown = element.all(by.css('.mat-expansion-panel')).get(0).all(by.css('mat-expansion-panel-header')).first();
    vakaSuhteetDropdown = element.all(by.css('.mat-expansion-panel')).get(1).all(by.css('mat-expansion-panel-header')).first();
    hakemus_pvm = element(by.id('hakemus_pvmvarhaiskasvatuspaatos_hakemusjapaatostiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    paatos_alkamis_pvm = element(by.id('alkamis_pvmvarhaiskasvatuspaatos_hakemusjapaatostiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    paatos_paattymis_pvm = element(by.id('paattymis_pvmvarhaiskasvatuspaatos_hakemusjapaatostiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    suhde_alkamis_pvm = element(by.id('alkamis_pvmvarhaiskasvatussuhde_perustiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();
    suhde_paattymis_pvm = element(by.id('paattymis_pvmvarhaiskasvatussuhde_perustiedot0')).all(by.css('div')).first().all(by.css('div')).first().all(by.css('input')).first();

    // Muokkaa lapsi toimipaikkaan form buttons
    savePaatosBtn = element(by.id('saveVarhaiskasvatuspaatosBtnWrapper0')).all(by.css('div')).first().all(by.css('button')).first();
    deletePaatosBtn = element(by.id('saveVarhaiskasvatuspaatosBtnWrapper0')).all(by.css('div')).get(1).all(by.css('button')).first();
    saveSuhdeBtn = element(by.id('saveVarhaiskasvatussuhdeBtnWrapper0')).all(by.css('div')).first().all(by.css('button')).first();
    deleteSuhdeBtn = element(by.id('saveVarhaiskasvatussuhdeBtnWrapper0')).all(by.css('div')).get(1).all(by.css('button')).first();

    // Kielipainotus form
    kielipainotuksetYesRadioBtn = element(by.id('kielipainotuksetYes'));
    addNewKielipainotusLink = element(by.id('addNewKielipainotusLink'));
    saveKielipainotusBtn = element(by.id('saveKielipainotus0'));
    kielipainotus_koodi = element(by.css('[name="kielipainotus_koodi"]'));
    kielipainotus_alkamis_pvm = element(by.css('[data-fieldname="alkamis_pvm"][data-parent-container="kielipainotus0"]'))
        .element(by.tagName('div'))
        .element(by.tagName('div'))
        .element(by.tagName('input'));

    // Toimintapainotus form
    toimintapainotuksetYesRadioBtn = element(by.id('toimintapainotuksetYes'));
    addNewToimintapainotusLink = element(by.id('addNewToimintapainotusLink'));
    saveToimintapainotusBtn = element(by.id('saveToimintapainotus0'));
    toimintapainotus_koodi = element(by.css('[name="toimintapainotus_koodi"]'));
    toimintapainotus_alkamis_pvm = element(by.css('[data-fieldname="alkamis_pvm"][data-parent-container="toimintapainotus0"]'))
        .element(by.tagName('div'))
        .element(by.tagName('div'))
        .element(by.tagName('input'));

    nextStepBtn = element(by.id('stepForwardBtn'));
    exitToimipaikkaFormBtn = element(by.id('exitToimipaikkaFormBtn'));
    deleteToimipaikkaBtn = element(by.id('deleteToimipaikkaBtn'));
    deleteToimipaikkaPromptModalLeave = element(by.id('deleteToimipaikkaPromptModalLeave'));

    fillKielipainotusForm(): any {
        const ec = protractor.ExpectedConditions;
        return this.kielipainotuksetYesRadioBtn.click()
            .then(() => {
                return browser.wait(ec.visibilityOf(this.addNewKielipainotusLink), 20000).then(() => this.addNewKielipainotusLink.click());
            }).then(() => {
                return this.kielipainotus_koodi.sendKeys('englan');
            }).then(() => {
                return element(by.id('EN')).click();
            })
            .then(() => this.kielipainotus_alkamis_pvm.sendKeys('01.01.2005'))
            .then(() => this.saveKielipainotusBtn.click());
    }

    fillToimintapainotusForm(): any {
        const ec = protractor.ExpectedConditions;
        return this.toimintapainotuksetYesRadioBtn.click().then(() => {
            return browser.wait(ec.visibilityOf(this.addNewToimintapainotusLink), 20000)
                .then(() => this.addNewToimintapainotusLink.click());
        }).then(() => this.toimintapainotus_koodi.all(by.tagName('option')).get(2).click())
            .then(() => this.toimintapainotus_alkamis_pvm.sendKeys('01.01.2005'))
            .then(() => this.saveToimintapainotusBtn.click());
    }

    fillToimipaikkaForm(): any {
        this.nimi.sendKeys(this.testText);
        this.kayntiosoite.sendKeys(this.testText);
        this.postinumero.sendKeys('20500');
        this.postitoimipaikka.sendKeys(this.testText);
        this.kunta_koodi.sendKeys('hel').then(() => {
            element(by.id('091')).click();
        });
        this.puhelinnumero.sendKeys('0401112222');
        this.sahkopostiosoite.sendKeys('protractortest@asdasdf.fi');
        this.toimintamuoto_koodi.all(by.tagName('option')).get(2).click();
        this.jarjestamismuoto_koodi_jm01.click();
        this.jarjestamismuoto_koodi_jm03.click();
        this.asiointikieli_koodi.sendKeys('suom').then(() => {
            element(by.id('FI')).click();
        });
        this.kasvatusopillinen_jarjestelma_koodi.all(by.tagName('option')).get(3).click();
        this.varhaiskasvatuspaikat.sendKeys('20');
        this.alkamis_pvm.sendKeys('01.01.2005');

        return this.saveToimipaikka();
    }

    fillAllToimipaikkaForms(): any {
        const ec = protractor.ExpectedConditions;
        return this.fillToimipaikkaForm().then(() => {
            return browser.sleep(3000);
        })
            .then(this.fillKielipainotusForm.bind(this))
            .then(this.nextStepBtn.click())
            .then(() => {
                return browser.sleep(3000);
            })
            .then(this.fillToimintapainotusForm.bind(this))
            .then(() => {
                return browser.sleep(3000);
            })
            .then(() => {
                return this.exitToimipaikkaFormBtn.click();
            });
    }

    deleteToimipaikkaWithoutHenkilo(): any {
        const ec = protractor.ExpectedConditions;
        return this.deleteToimipaikkaBtn.click()
            .then(() => {
                return browser.sleep(2000);
            })
            .then(() => this.deleteToimipaikkaPromptModalLeave.click())
            .then(() => {
                return browser.sleep(5000);
            });
    }

    saveToimipaikka(): any {
        return this.saveToimipaikkaBtn.click();
    }
}
