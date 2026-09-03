/*
* Used for outputting contents of fi.json to sv.json
*/
const fs = require('fs');
const path = require('path');    
const filePath = path.join(__dirname, 'fi.json');
const args = process.argv.slice(2);
fs.readFile(filePath, 'utf8', (err, data) => {
    data = JSON.parse(data);
    const keys = Object.keys(data);
    const keyValuePair = {};
    for (let x = 0; x < keys.length; x++) {
        const key = keys[x];
        const value = data[keys[x]];
        let suffix;
        let formattedTranslationValue = value;
        if (args.length === 1) {
            suffix = args[0];
        }

        if (suffix) {
            formattedTranslationValue = `${value}${suffix}`;
        }

        keyValuePair[key] = formattedTranslationValue;
    }
    const jsonStr = JSON.stringify(keyValuePair);
    fs.writeFile(path.join(__dirname, 'sv.json'), jsonStr, 'utf8', callback);
});

const callback = (e) => {
    console.log(e);
}