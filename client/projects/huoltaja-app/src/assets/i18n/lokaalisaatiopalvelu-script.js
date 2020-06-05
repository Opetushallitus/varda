const vardaArr = {
  "page.title": "Varhaiskasvatustiedot – Oma Opintopolku",
  "varhaiskasvatustiedot": "Varhaiskasvatustiedot",
  "varhaiskasvatustiedot.toimipaikoittain": "Varhaiskasvatustiedot toimipaikoittain",
  "varhaiskasvatustiedot.text-p1": "Tällä sivulla näkyvät kaikki Vardaan tallennetut henkilö- ja varhaiskasvatustiedot uusimmasta vanhimpaan. Tiedot tallentaa varhaiskasvatuksen järjestäjä.",
  "varhaiskasvatustiedot.text-p2": "Varhaiskasvatuksen tietovaranto Varda kokoaa tiedot varhaiskasvatuksessa olevista lapsista, toimipaikoista, huoltajista, maksuista sekä henkilöstöstä. Varhaiskasvatustoimijat eli kunnat, kuntayhtymät ja yksityiset varhaiskasvatuksen palveluntuottajat tallentavat tiedot Vardaan. Tietovarannosta tiedot välitetään eteenpäin lakiperusteisesti tiedon tarvitsijoille, kuten opetus- ja kulttuuriministeriölle, aluehallintavirastoille, Kelalle ja Tilastokeskukselle. Tietojen tallentaminen perustuu varhaiskasvatuslakiin (540/2018).",
  "varhaiskasvatuspaatos.ei-vakapaatoksia": "Lapselta ei löydy varhaiskasvatuspäätöksiä",
  "label.henkilotiedot": "Henkilötiedot",
  "label.katsot-tietoja-huoltajana": "Katsot tietoja huoltajana",
  "label.henkilotiedot-varjaiskasvatuksen-tietovarannossa": "Henkilötiedot varhaiskasvatuksen tietovarannossa",
  "lapsi.oppijanumero": "Oppijanumero",
  "lapsi.henkilotunnus": "Henkilötunnus",
  "lapsi.etunimet": "Etunimet",
  "lapsi.kutsumanimi": "Kutsumanimi",
  "lapsi.sukunimi": "Sukunimi",
  "lapsi.aidinkieli": "Äidinkieli",
  "lapsi.syntymaaika": "Syntymäaika",
  "lapsi.sukupuoli": "Sukupuoli",
  "lapsi.kotikunta": "Kotikunta",
  "lapsi.katuosoite": "Katuosoite",
  "lapsi.postinumero": "Postinumero",
  "lapsi.postitoimipaikka": "Postitoimipaikka",
}


const sendTranslation = (key, value, lang = "fi") => {
  const cookie = document.cookie.split(";").map(c => c.trim())
  const csrf = cookie.find(c => c.startsWith("CSRF=")).slice(16, 99)
  const xhttp = new XMLHttpRequest();
  xhttp.open("POST", "https://virkailija.testiopintopolku.fi/lokalisointi/cxf/rest/v1/localisation", true);
  xhttp.setRequestHeader("Content-type", "application/json");
  xhttp.setRequestHeader("csrf", csrf);
  const d = JSON.stringify({
    category: "varda-huoltaja",
    locale: lang,
    key: key,
    value: value
  });

  xhttp.send(d);
};

Object.keys(vardaArr).forEach(key => sendTranslation(key, vardaArr[key]));
Object.keys(vardaArr).forEach(key => sendTranslation(key, `TODO ${key}`, "sv"));



// paste konsoliin, olemassaolevat avaimet ignorautuu
