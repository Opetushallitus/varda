import { VardaFormValidators } from './varda-form-validators';
import { FormControl, FormGroup} from '@angular/forms';

describe('VardaFormValidators', () => {
    it('Should check that nickname is part of firstname, is not a substring of any of the firstnames and contains only one name', () => {
        const henkiloForm1 = new FormGroup({firstnames: new FormControl('Marja-Liisa Tuuli'), nickname: new FormControl('Tuuli')});
        const henkiloForm2 = new FormGroup({firstnames: new FormControl('Marja-Liisa Tuuli'), nickname: new FormControl('Marja Tuuli')});
        const henkiloForm3 = new FormGroup({firstnames: new FormControl('Marja-Liisa'), nickname: new FormControl('asdf')});
        const henkiloForm4 = new FormGroup({firstnames: new FormControl('Marja-Liisa Annikki'), nickname: new FormControl('')});
        const henkiloForm5 = new FormGroup({firstnames: new FormControl(''), nickname: new FormControl('asdfasfasdfasd')});
        const henkiloForm6 = new FormGroup({firstnames: new FormControl('Marja-Liisa Annikki Tuuli'),
        nickname: new FormControl('Anni')});
        const henkiloForm7 = new FormGroup({firstnames: new FormControl('Annikki Liisa-Marja Tuuli Testinpoika'),
        nickname: new FormControl('Liisa-Marja')});
        const henkiloForm8 = new FormGroup({firstnames: new FormControl('Annikki Liisa-Marja Tuuli Testinpoika'),
        nickname: new FormControl('Annikki')});
        const henkiloForm9 = new FormGroup({firstnames: new FormControl('Annikki Liisa-Marja Tuuli Testinpoika'),
        nickname: new FormControl('Marja-Liisa')});

        const res1 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm1);
        const res2 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm2);
        const res3 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm3);
        const res4 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm4);
        const res5 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm5);
        const res6 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm6);
        const res7 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm7);
        const res8 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm8);
        const res9 = VardaFormValidators.nicknamePartOfFirstname(henkiloForm9);

        expect(res1).toBeNull();
        expect(res2).toEqual({nicknameMustBeOneName: true});
        expect(res3).toEqual({nicknameNotPartOfFirstname: true});
        expect(res4).toBeNull();
        expect(res5).toBeNull();
        expect(res6).toEqual({nicknameNotPartOfFirstname: true});
        expect(res7).toBeNull();
        expect(res8).toBeNull();
        expect(res9).toEqual({nicknameNotPartOfFirstname: true});
    });
});
