import pytesseract
from PIL import Image
import re
import json
from scrape import read_jsonlines, jsonlines_path, jsonlines_to_csv
import shutil


# Some regexes for checking TODI well-formedness (not currently used); they don't implement ALL the TODI rules yet.
accent = r'(!?(H\*LH|L\*HL|H\*L|L\*H|H\*|L\*|H\*!H))'
optional_accent = rf'(\({accent}\))'
accent = fr'({accent}|{optional_accent})'
initial = r'(%|%H|%L)'
final = r'(%|H%|L%)'
ip = fr'({initial} ({accent} )+{final})'
todi_regex = fr'({ip})( {ip})*'


def main():

    shutil.copyfile(jsonlines_path, jsonlines_path + '.ocr_backup')
    print('I made a backup of', jsonlines_path)

    items = read_jsonlines(jsonlines_path)
    with open(jsonlines_path, 'w') as json_writer:
        for item in items:
            if item['type'] == 'example':
                image_path = f'scraped/{item["image_file"]}'
                print(image_path)
                words, todi = todi_from_image(image_path)
                if words:
                    item['words_ocr'], item['todi_ocr'] = ' '.join(words), ' '.join(todi)
            json_writer.write(json.dumps(item) + '\n')

    jsonlines_to_csv(jsonlines_path)


def todi_from_image(image):
    try:
        image = Image.open(image)
    except Exception:
        return None, None

    x, y = image.size
    image = image.crop((0, y - 40, x, y))

    ocr_result = pytesseract.image_to_string(image, lang='nld')

    if len(ocr_result) < 5:
        return None, None
    lines = [line.strip() for line in ocr_result.splitlines()]

    wordlines = []
    todilines = []
    for line in lines:
        if '%' in line or '*' in line:
            todilines.append(line)
        else:
            wordlines.append(line)

    todi = ' '.join(todilines)
    words = ' '.join(wordlines)
    todi = clean_todi(todi)

    words = words.split()
    todi = todi.split()

    return words, todi



todi_corrections = {
    '(L)': '(L*)',
    '(H)': '(H*)',
    'L-': 'L*',
    '°': '*',
    'IH': '!H',
    'MH': '!H',
    # 'IH*L': '!H*L',
    'HE"': 'H*',
    'HH': 'H*!H',
    'HE': 'H*',
    'HEL': 'H*L',
    'HS': 'H*',
    'HT': 'H*',
    'H-': 'H*',
    '%LH*': '%L H*',
    'LH': 'L*H',
    'HL': 'H*L',
    '%L_': '%L ',
    'Yol': '%L',
    'H"': 'H*',
    '__H%': 'H%',
    'e%L': '%L',
    'H2': 'H%',
    '{': '(',
    '9': 'L%',
    'VL': '%L',
    'Lol': '%L',
}

todi_corrections_re = {
    r'H\* !H(?!\*)': 'H*!H',
    r'L\*H\*L': 'L*HL',
    r'H\*L\*H': 'H*LH',
    r'He(?![a-z])': 'H*',
    r'Ho(?![a-z])': 'H%',
    r'Hi(?![a-z])': 'H*',
}

todi_corrections_piecewise = {
    '-': 'H*',
    '_': '',
}

def clean_todi(todi):
    for key, val in sorted(todi_corrections.items(), key=lambda t: len(t[0]), reverse=True):
        todi = todi.replace(key, val)
    for key, val in todi_corrections_re.items():
        todi = re.sub(key, val, todi)
    todi_split = todi.split()
    todi_split = [todi_corrections_piecewise.get(t, t) for t in todi_split]
    return re.sub('\s+', ' ', ' '.join(todi_split))



if __name__ == '__main__':
    main()