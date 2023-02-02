import os
import urllib.parse
from urllib.request import urlopen
import bs4
import re
import pandas as pd
import json
import random

random.seed(123456)

BASE_URL = 'https://todi.cls.ru.nl/ToDI/'
OUT_DIR = 'scraped'

jsonlines_path = f'{OUT_DIR}/index.jsonlines'

def main():

    os.makedirs(f'{OUT_DIR}', exist_ok=True)
    os.makedirs(f'{OUT_DIR}/exercises', exist_ok=True)
    os.makedirs(f'{OUT_DIR}/examples', exist_ok=True)

    page_urls, exercise_urls = crawl_menu()

    with open(jsonlines_path, 'w') as json_writer:

        for exercise_url in exercise_urls:
            crawl_exercise(exercise_url, json_writer)

        for page_url in page_urls:
            crawl_page(page_url, json_writer)

    jsonlines_to_csv(jsonlines_path)


def jsonlines_to_csv(jsonlines_path):
    jsonlines = read_jsonlines(jsonlines_path)

    df = pd.DataFrame(jsonlines).set_index('index', drop=True)
    df = df[['words','todi','words_ocr','todi_ocr','sound_file','image_file','type','page_title','exercise_id','sound_url','image_url','page_url','words_sep','todi_sep']]
    df.to_csv(jsonlines_path.replace('.jsonlines', '.csv'))


def read_jsonlines(path):
    with open(path, 'r') as json_reader:
        jsonlines = [json.loads(line.strip()) for line in json_reader if line.strip()]

    return jsonlines


def crawl_menu():

    menu_url = 'https://todi.cls.ru.nl/ToDI/contents.htm'

    exercise_urls = []
    page_urls = []

    with urlopen(menu_url) as htmlreader:
        todi_menu = bs4.BeautifulSoup(htmlreader, 'html.parser')

    for url in todi_menu.find_all('a'):
        if url['href'].startswith('javascript'):
            entry_url = BASE_URL + re.search(r'\(\'([^\',]*)\',', url['href']).group(1)

            with urlopen(entry_url) as htmlreader:
                entry_page = bs4.BeautifulSoup(htmlreader, 'html.parser')

            tag = entry_page.find('frame', {'name': 'mainFrame'})

            if tag:
                entry_url_base = entry_url.rsplit("/", maxsplit=1)[0]
                first_exercise_url = f'{entry_url_base}/{tag["src"]}'

                with urlopen(first_exercise_url) as htmlreader:
                    first_exercise_page = bs4.BeautifulSoup(htmlreader, 'html.parser')

                for sub_exercise in first_exercise_page.find_all('input', {'onclick': lambda x: x and x.startswith('ChooseExerc')}):
                    sub_exercise_num = re.search(r'Exercise.value,\'(\d+)\'', sub_exercise['onclick'])
                    if not sub_exercise_num:
                        continue

                    subexercise_url = first_exercise_url.rsplit('_', maxsplit=1)[0] + '_' + sub_exercise_num.group(1) + '.htm'
                    exercise_urls.append(subexercise_url)

        else:
            page_urls.append(urllib.parse.urljoin(BASE_URL, url['href']))

    return page_urls, exercise_urls


def crawl_page(page_url, json_writer):

    print(page_url)
    all_meta = []

    with urlopen(page_url) as htmlreader:
        todi_page = bs4.BeautifulSoup(htmlreader, 'html.parser')

    for table in todi_page.find_all('table', {'onclick': lambda x: x and x.startswith('play_sound')}):
        meta = crawl_example(table, page_url, todi_page.title.text, json_writer)
        all_meta.append(meta)

    return all_meta


def crawl_example(table, page_url, page_title, json_writer):
    meta = {
        'page_url': page_url,
        'type': 'example',
        'page_title': page_title,
    }

    sound_match = re.search('\'([^\']*)\'', table['onclick'])
    image_match = table.find_next('img', {'src': lambda x: x.startswith('./audio')})

    if sound_match:
        sound_url = sound_match.group(1).replace('./', BASE_URL) + '.wav'
        meta['sound_url'] = sound_url
        meta['index'] = sound_url.rsplit('/', maxsplit=1)[-1].split('.')[0]
        try:
            with urlopen(sound_url) as soundreader:
                sound = soundreader.read()
            sound_filename = f'examples/{meta["index"]}.wav'
            meta['sound_file'] = sound_filename
            with open(f'{OUT_DIR}/{sound_filename}', 'wb') as soundwriter:
                soundwriter.write(sound)
        except Exception as e:   # HTTPError...
            print(sound_url, e)

    if image_match:
        image_url = image_match['src'].replace('./', BASE_URL)
        with urlopen(image_url) as imagereader:
            image = imagereader.read()
        meta['image_url'] = image_url
        if not 'index' in meta:
            meta['index'] = image_url.rsplit('/', maxsplit=1)[-1].split('.')[0]
        image_filename = f'examples/{meta["index"]}{os.path.splitext(image_url)[-1]}'
        meta['image_file'] = image_filename
        with open(f'{OUT_DIR}/{image_filename}', 'wb') as imagewriter:
            imagewriter.write(image)

    json_writer.write(json.dumps(meta) + '\n')

    return meta


def crawl_exercise(exercise_url, json_writer):
    print(exercise_url)

    meta = {'type': 'exercise', 'page_url': exercise_url}

    with urlopen(exercise_url) as htmlreader:
        exercise_page = bs4.BeautifulSoup(htmlreader, 'html.parser')

    exercise_url_base = exercise_url.rsplit("/", maxsplit=1)[0]

    answer = exercise_page.find('input', {'name': 'ToDIAnswer'})
    transcription_table = exercise_page.find('table', {'bgcolor': 'lightgrey', 'border': '0', 'cellpadding': '1', 'cellspacing': '0'})

    sound_table = exercise_page.find('td', {'onclick': lambda x: x and x.startswith('play_sound')}, recursive=True)
    image_button = exercise_page.find('input', {'onclick': lambda x: x and x.startswith("HintsWindow('F0-contour'")}, recursive=True)

    uiting_field = exercise_page.find('input', {'name': 'Uiting'})
    if uiting_field:
        meta['index'] = uiting_field['value']

    exercise_id_field = exercise_page.find('input', {'name': 'Exercise'})
    if exercise_id_field:
        exercise_id = exercise_id_field['value']
        meta['exercise_id'] = exercise_id

    if answer:
        todi = [s.replace('---', '').strip() for s in answer['value'].split()]
        meta['todi_sep'] = '|'.join(todi)
        meta['todi'] = ' '.join(todi)

    if transcription_table:
        words = [tag.text.replace('\xa0', '').strip() for tag in transcription_table.find('tr').find_all('td', {'align': 'center'})][1:]
        meta['words_sep'] = '|'.join(words)
        meta['words'] = ' '.join(words)

    if sound_table:
        sound_match = re.search('\'([^\']*)\'', sound_table['onclick'])
        sound_url = exercise_url_base + '/' + sound_match.group(1) + '.wav'
        if not 'index' in meta:
            meta['index'] = sound_match.group(1)
        with urlopen(sound_url) as soundreader:
            sound = soundreader.read()
        meta['sound_url'] = sound_url
        sound_file = f'exercises/{meta["index"]}.wav'
        meta['sound_file'] = sound_file
        with open(f'{OUT_DIR}/{sound_file}', 'wb') as soundwriter:
            soundwriter.write(sound)

    if image_button:
        image_url = exercise_url_base + '/' + re.search(r'SRC= ([^.]+\.(?:png|gif))', image_button['onclick']).group(1)
        image_url = image_url.replace(r'\\', r'//') # weird bug with https://todi.cls.ru.nl/ToDI/ToDIpraat_3b/audio\\png\\239.png
        meta['image_url'] = image_url
        try:
            with urlopen(image_url) as imagereader:
                image = imagereader.read()
            image_file = f'exercises/{meta["index"]}{os.path.splitext(image_url)[-1]}'
            meta['image_file'] = image_file
            with open(f'{OUT_DIR}/{image_file}', 'wb') as imagewriter:
                imagewriter.write(image)
        except Exception as e:
            print(image_url, e)

    json_writer.write(json.dumps(meta) + '\n')

    return meta



if __name__ == '__main__':
    main()