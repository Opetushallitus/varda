import { utils } from './test-utils';
import { DashboardPage } from './pageobjects/dashboard.po';
import { ToimipaikkaFormPage } from './pageobjects/toimipaikka-form.po';
import { browser, protractor } from 'protractor';

describe('Toimipaikka e2e-tests', () => {
  let dashboardPage: DashboardPage;
  let toimipaikkaFormPage: ToimipaikkaFormPage;
  const ec = protractor.ExpectedConditions;
  const WAITDASHBOARD = 20000;
  const ELEMENT = `-element did not appear in DOM in ${WAITDASHBOARD / 1000} seconds`;
  const MESSAGE = `-message did not appear in DOM in ${WAITDASHBOARD / 1000} seconds`;
  const HEADER_ERROR_MSG = `Header did not appear in DOM in ${WAITDASHBOARD / 1000} seconds`;

  // Generate random name for toimipaikka like 'Toimipaikka <random_string_8_chars>'
  // e.g. 'Toimipaikka f0j82k9q' or 'Toimipaikka 5alvubv7'
  const toimipaikanNimi = 'Toimipaikka ' + Math.random().toString(36).substr(2, 8);

  beforeAll(() => {
    dashboardPage = new DashboardPage();
    dashboardPage.navigateToDashboard();
  });

  beforeEach(() => {
    toimipaikkaFormPage = new ToimipaikkaFormPage();
    browser.sleep(1000);
  });

  afterEach(() => { });

  it('Add toimipaikka - positive case', () => {
    browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), WAITDASHBOARD, HEADER_ERROR_MSG);
    utils.closeCookieButton();
    utils.selectNextDropdownOption(dashboardPage.toimipaikkaSelector);

    // Click 'Lisää toimipaikka' -button and start filling
    utils.clickElement(dashboardPage.addToimipaikkaBtn);
    browser.wait(ec.presenceOf(toimipaikkaFormPage.nimi), WAITDASHBOARD, 'Toimipaikan nimi' + ELEMENT);
    toimipaikkaFormPage.nimi.sendKeys(toimipaikanNimi);
    toimipaikkaFormPage.kayntiosoite.sendKeys('Mallikatu 1 A');
    toimipaikkaFormPage.kayntiosoite_postinumero.sendKeys('02100');
    toimipaikkaFormPage.kayntiosoite_postitoimipaikka.sendKeys('Esimerkkikatu 12');
    toimipaikkaFormPage.postiosoite.sendKeys('Esimerkkikatu 12');
    toimipaikkaFormPage.postinumero.sendKeys('02100');
    toimipaikkaFormPage.postitoimipaikka.sendKeys('Espoo');

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.toimintamuoto_koodi).perform();
    utils.selectNextDropdownOption(toimipaikkaFormPage.kunta_koodi);
    toimipaikkaFormPage.puhelinnumero.sendKeys('+358401234567');
    toimipaikkaFormPage.sahkopostiosoite.sendKeys('joku@osoite.fi');

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.asiointikieli_koodi).perform();
    utils.selectNextDropdownOption(toimipaikkaFormPage.toimintamuoto_koodi);
    utils.clickElement(toimipaikkaFormPage.jarjestamismuoto_koodi_jm01);
    utils.clickElement(toimipaikkaFormPage.jarjestamismuoto_koodi_jm03);

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.varhaiskasvatuspaikat).perform();
    utils.selectNextDropdownOption(toimipaikkaFormPage.asiointikieli_koodi);
    utils.selectNextDropdownOption(toimipaikkaFormPage.kasvatusopillinen_jarjestelma_koodi);
    toimipaikkaFormPage.varhaiskasvatuspaikat.sendKeys('1');
    toimipaikkaFormPage.alkamis_pvm.sendKeys('01.04.2019');

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.paattymis_pvm).perform();
    toimipaikkaFormPage.paattymis_pvm.sendKeys('31.12.2029');

    // Scroll down and save
    browser.executeScript('window.scrollTo(0,10000);').then(function () {
      utils.clickElement(toimipaikkaFormPage.saveToimipaikkaBtn);
    });

    // Check everything is correct
    browser.wait(ec.presenceOf(toimipaikkaFormPage.tallennusOnnistuiAlert), WAITDASHBOARD, 'Tallennus onnistui ' + MESSAGE);
    expect(toimipaikkaFormPage.dialogTitleLabel.getText()).toEqual(toimipaikanNimi);
    expect(toimipaikkaFormPage.tallennusOnnistuiAlert.getText()).toEqual('Tallennus onnistui');

    // Close the modal
    browser.actions().sendKeys(protractor.Key.ESCAPE).perform();
  });

  it('Edit toimipaikka - positive case', () => {
    browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), WAITDASHBOARD, HEADER_ERROR_MSG);
    utils.closeCookieButton();

    // Choose correct toimipaikka and start filling
    utils.selectDropdownOptionByText(dashboardPage.toimipaikkaSelector, toimipaikanNimi);
    utils.clickElement(dashboardPage.editToimipaikkaBtn);
    browser.wait(ec.presenceOf(toimipaikkaFormPage.nimi), WAITDASHBOARD, 'Toimipaikan nimi' + ELEMENT);
    toimipaikkaFormPage.kayntiosoite.clear();
    toimipaikkaFormPage.kayntiosoite.sendKeys('Mallikatu 1 B');
    toimipaikkaFormPage.kayntiosoite_postinumero.clear();
    toimipaikkaFormPage.kayntiosoite_postinumero.sendKeys('02200');
    toimipaikkaFormPage.kayntiosoite_postitoimipaikka.clear();
    toimipaikkaFormPage.kayntiosoite_postitoimipaikka.sendKeys('Esimerkkikatu 15');
    toimipaikkaFormPage.postiosoite.clear();
    toimipaikkaFormPage.postiosoite.sendKeys('Esimerkkikatu 15');
    toimipaikkaFormPage.postinumero.clear();
    toimipaikkaFormPage.postinumero.sendKeys('02200');
    toimipaikkaFormPage.postitoimipaikka.clear();
    toimipaikkaFormPage.postitoimipaikka.sendKeys('Helsinki');

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.toimintamuoto_koodi).perform();
    utils.selectNextDropdownOption(toimipaikkaFormPage.kunta_koodi);
    toimipaikkaFormPage.puhelinnumero.clear();
    toimipaikkaFormPage.puhelinnumero.sendKeys('+358401234568');
    toimipaikkaFormPage.sahkopostiosoite.clear();
    toimipaikkaFormPage.sahkopostiosoite.sendKeys('jokutoinen@osoite.fi');

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.asiointikieli_koodi).perform();
    utils.clickElement(toimipaikkaFormPage.jarjestamismuoto_koodi_jm01);
    utils.clickElement(toimipaikkaFormPage.jarjestamismuoto_koodi_jm02);
    utils.clickElement(toimipaikkaFormPage.jarjestamismuoto_koodi_jm03);
    utils.clickElement(toimipaikkaFormPage.jarjestamismuoto_koodi_jm04);

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.varhaiskasvatuspaikat).perform();
    utils.selectNextDropdownOption(toimipaikkaFormPage.asiointikieli_koodi);
    utils.selectNextDropdownOption(toimipaikkaFormPage.kasvatusopillinen_jarjestelma_koodi);
    toimipaikkaFormPage.varhaiskasvatuspaikat.clear();
    toimipaikkaFormPage.varhaiskasvatuspaikat.sendKeys('2');
    toimipaikkaFormPage.alkamis_pvm.clear();
    toimipaikkaFormPage.alkamis_pvm.sendKeys('02.04.2019');

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.paattymis_pvm).perform();
    toimipaikkaFormPage.paattymis_pvm.clear();
    toimipaikkaFormPage.paattymis_pvm.sendKeys('30.12.2029');

    // Scroll down and save
    browser.executeScript('window.scrollTo(0,10000);').then(function () {
      utils.clickElement(toimipaikkaFormPage.saveToimipaikkaBtn);
    });

    // Check everything is correct
    browser.wait(ec.presenceOf(toimipaikkaFormPage.tallennusOnnistuiAlert), WAITDASHBOARD, 'Tallennus onnistui ' + MESSAGE);
    expect(toimipaikkaFormPage.dialogTitleLabel.getText()).toEqual(toimipaikanNimi);
    expect(toimipaikkaFormPage.tallennusOnnistuiAlert.getText()).toEqual('Tallennus onnistui');

    // Close the modal
    browser.actions().sendKeys(protractor.Key.ESCAPE).perform();
  });

  it('Lisää lapsi henkilötunnuksella - positive case', () => {
    browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), WAITDASHBOARD, HEADER_ERROR_MSG);
    utils.closeCookieButton();

    // Select correct toimipaikka and click "Lisää lapsi" -button
    utils.selectDropdownOptionByText(dashboardPage.toimipaikkaSelector, toimipaikanNimi);
    utils.clickElement(dashboardPage.addHenkiloBtn);

    // Fill the first part of the form and proceed
    browser.wait(ec.presenceOf(toimipaikkaFormPage.henkilotunnus), WAITDASHBOARD, 'Henkilötunnus ' + ELEMENT);
    toimipaikkaFormPage.henkilotunnus.sendKeys('160618A8773');
    toimipaikkaFormPage.etunimet.sendKeys('Matti Erik');
    toimipaikkaFormPage.kutsumanimi.sendKeys('Matti');
    toimipaikkaFormPage.sukunimi.sendKeys('Meikäläinen');
    utils.clickElement(toimipaikkaFormPage.lisaaLapsiBtn);

    // Fill the second part of the form
    browser.wait(ec.elementToBeClickable(toimipaikkaFormPage.vaka_alkamis_pvm), WAITDASHBOARD, 'Varhaiskasvatuksen alkamispäivä ' + ELEMENT);
    toimipaikkaFormPage.vaka_alkamis_pvm.sendKeys('02.03.2019');

    // Scroll down and continue filling
    browser.actions().mouseMove(toimipaikkaFormPage.vaka_paattymis_pvm).perform();
    toimipaikkaFormPage.vaka_paattymis_pvm.sendKeys('31.12.2029');
    browser.actions().mouseMove(toimipaikkaFormPage.hakemus_pvm).perform();
    toimipaikkaFormPage.hakemus_pvm.sendKeys('01.03.2019');
    browser.actions().mouseMove(toimipaikkaFormPage.hakemus_alkamis_pvm).perform();
    toimipaikkaFormPage.hakemus_alkamis_pvm.sendKeys('01.03.2019');
    browser.actions().mouseMove(toimipaikkaFormPage.hakemus_paattymis_pvm).perform();
    toimipaikkaFormPage.hakemus_paattymis_pvm.sendKeys('31.12.2029');
    browser.actions().mouseMove(toimipaikkaFormPage.tuntimaara_viikossa).perform();
    utils.selectNextDropdownOption(toimipaikkaFormPage.jarjestamismuoto_koodi);
    toimipaikkaFormPage.tuntimaara_viikossa.sendKeys('40');

    // Scroll down and save
    browser.actions().mouseMove(toimipaikkaFormPage.lisaaLapsiBtn).perform();
    utils.clickElement(toimipaikkaFormPage.paivittainen_vaka);
    utils.clickElement(toimipaikkaFormPage.kokopaivainen_vaka);
    utils.clickElement(toimipaikkaFormPage.lisaaLapsiBtn);

    // Check everything is correct
    browser.wait(ec.presenceOf(toimipaikkaFormPage.editLapsiBtn), WAITDASHBOARD, 'Edit child button ' + ELEMENT);
    expect(toimipaikkaFormPage.editLapsiBtn.getText()).toEqual('Meikäläinen, Matti Erik');

    // Wait till success message is gone
    browser.wait(utils.searchByCssStyle(toimipaikkaFormPage.lapsiSuccessModal, 'display: none;'), WAITDASHBOARD);
  });

  it('Muokkaa lapsen varhaiskasvatussuhde - positive case', () => {
    browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), WAITDASHBOARD, HEADER_ERROR_MSG);
    utils.closeCookieButton();

    // Select correct child and click
    utils.selectDropdownOptionByText(dashboardPage.toimipaikkaSelector, toimipaikanNimi);
    const editLapsiBtnOikeaToimipaikka = element(by.css('p[class="varda-henkilo-item-entry"]'));
    utils.clickElement(editLapsiBtnOikeaToimipaikka);

    // Fill the form and proceed
    browser.wait(ec.presenceOf(toimipaikkaFormPage.vakaSuhteetDropdown), WAITDASHBOARD, 'Varhaiskasvatussuhteet dropdown ' + ELEMENT);
    utils.clickElement(toimipaikkaFormPage.vakaSuhteetDropdown);
    toimipaikkaFormPage.suhde_alkamis_pvm.clear();
    toimipaikkaFormPage.suhde_alkamis_pvm.sendKeys('03.03.2019');
    toimipaikkaFormPage.suhde_paattymis_pvm.clear();
    toimipaikkaFormPage.suhde_paattymis_pvm.sendKeys('30.12.2029');

    // Scroll down and save
    browser.actions().mouseMove(toimipaikkaFormPage.saveSuhdeBtn).perform();
    utils.clickElement(toimipaikkaFormPage.saveSuhdeBtn);

    // Check everything is correct
    browser.wait(ec.presenceOf(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert), WAITDASHBOARD, 'Tallennus onnistui ' + ELEMENT);
    expect(toimipaikkaFormPage.vakaSuhteetDropdown.getText()).toEqual('Varhaiskasvatussuhde 03.03.2019 - 30.12.2029');
    expect(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert.getText()).toEqual('Tallennus onnistui');

    // Close the modal
    utils.clickElement(element(by.css('button[class="close"]')));
    const poistuLomakkeeltaButton = element(by.id('henkiloPromptModalLeave'))
    browser.wait(ec.elementToBeClickable(poistuLomakkeeltaButton), WAITDASHBOARD, 'Poistu lomakkeelta button ' + ELEMENT);
    utils.clickElement(poistuLomakkeeltaButton);
  });

  it('Poista lapsen varhaiskasvatussuhde - positive case', () => {
    browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), WAITDASHBOARD, HEADER_ERROR_MSG);
    utils.closeCookieButton();

    // Select correct child and click
    utils.selectDropdownOptionByText(dashboardPage.toimipaikkaSelector, toimipaikanNimi);
    const editLapsiBtnOikeaToimipaikka = element(by.css('p[class="varda-henkilo-item-entry"]'));
    utils.clickElement(editLapsiBtnOikeaToimipaikka);

    // Scroll down and press delete button
    browser.wait(ec.presenceOf(toimipaikkaFormPage.vakaSuhteetDropdown), WAITDASHBOARD, 'Varhaiskasvatussuhteet dropdown ' + ELEMENT);
    utils.clickElement(toimipaikkaFormPage.vakaSuhteetDropdown);
    browser.actions().mouseMove(toimipaikkaFormPage.deleteSuhdeBtn).perform();
    utils.clickElement(toimipaikkaFormPage.deleteSuhdeBtn);

    // Confirm and delete
    const deleteLapsiBtnConfirm = element(by.id('varhaiskasvatussuhdeConfirmDeleteBtn0'));
    utils.clickElement(deleteLapsiBtnConfirm);
    browser.wait(ec.presenceOf(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert), WAITDASHBOARD, 'lapsiTallennusOnnistuiAlert ' + ELEMENT);

    // Check everything is correct
    expect(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert.getText()).toEqual('Varhaiskasvatussuhteen mitätöinti onnistui');

    // Close the modal
    utils.clickElement(element(by.css('button[class="close"]')));
  });

  it('Muokkaa lapsen varhaiskasvatuspäätös - positive case', () => {
    browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), WAITDASHBOARD, HEADER_ERROR_MSG);
    utils.closeCookieButton();

    // Select correct child and click
    utils.selectDropdownOptionByText(dashboardPage.toimipaikkaSelector, toimipaikanNimi);
    const editLapsiBtnOikeaToimipaikka = element(by.css('p[class="varda-henkilo-item-entry"]'));
    utils.clickElement(editLapsiBtnOikeaToimipaikka);

    // Fill the form and proceed
    browser.wait(ec.presenceOf(toimipaikkaFormPage.vakaPaatoksetDropdown), WAITDASHBOARD, 'Varhaiskasvatuspäätökset dropdown ' + ELEMENT);
    utils.clickElement(toimipaikkaFormPage.vakaPaatoksetDropdown);
    toimipaikkaFormPage.hakemus_pvm.clear();
    toimipaikkaFormPage.hakemus_pvm.sendKeys('01.01.2019');
    toimipaikkaFormPage.paatos_alkamis_pvm.clear();
    toimipaikkaFormPage.paatos_alkamis_pvm.sendKeys('02.02.2019');
    toimipaikkaFormPage.paatos_paattymis_pvm.clear();
    toimipaikkaFormPage.paatos_paattymis_pvm.sendKeys('31.12.2030');

    // Scroll down and save
    browser.actions().mouseMove(toimipaikkaFormPage.savePaatosBtn).perform();
    utils.clickElement(toimipaikkaFormPage.savePaatosBtn);

    // Check everything is correct
    browser.wait(ec.presenceOf(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert), WAITDASHBOARD, 'Tallennus onnistui ' + ELEMENT);
    expect(toimipaikkaFormPage.vakaPaatoksetDropdown.getText()).toEqual('Varhaiskasvatuspäätös 02.02.2019 - 31.12.2030');
    expect(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert.getText()).toEqual('Tallennus onnistui');

    // Close the modal
    utils.clickElement(element(by.css('button[class="close"]')));
    const poistuLomakkeeltaButton = element(by.id('henkiloPromptModalLeave'))
    browser.wait(ec.elementToBeClickable(poistuLomakkeeltaButton), WAITDASHBOARD, 'Poistu lomakkeelta button ' + ELEMENT);
    utils.clickElement(poistuLomakkeeltaButton);
  });

  it('Poista lapsen varhaiskasvatuspäätös ja lapsi - positive case', () => {
    browser.wait(ec.presenceOf(dashboardPage.vardaHeaderLinks.get(0)), WAITDASHBOARD, HEADER_ERROR_MSG);
    utils.closeCookieButton();

    // Select correct child and click
    utils.selectDropdownOptionByText(dashboardPage.toimipaikkaSelector, toimipaikanNimi);
    const editLapsiBtnOikeaToimipaikka = element(by.css('p[class="varda-henkilo-item-entry"]'));
    utils.clickElement(editLapsiBtnOikeaToimipaikka);

    // Scroll down and press delete button
    browser.wait(ec.presenceOf(toimipaikkaFormPage.vakaPaatoksetDropdown), WAITDASHBOARD, 'Varhaiskasvatuspäätökset dropdown ' + ELEMENT);
    utils.clickElement(toimipaikkaFormPage.vakaPaatoksetDropdown);
    browser.actions().mouseMove(toimipaikkaFormPage.deletePaatosBtn).perform();
    utils.clickElement(toimipaikkaFormPage.deletePaatosBtn);

    // Confirm and delete
    const deleteLapsiBtnConfirm = element(by.id('varhaiskasvatuspaatosConfirmDeleteBtn0'));
    utils.clickElement(deleteLapsiBtnConfirm);
    browser.wait(ec.presenceOf(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert), WAITDASHBOARD, 'lapsiTallennusOnnistuiAlert ' + ELEMENT);

    // Check everything is correct
    expect(toimipaikkaFormPage.lapsiTallennusOnnistuiAlert.getText()).toEqual('Varhaiskasvatuspäätöksen mitätöinti onnistui');
  });
});
