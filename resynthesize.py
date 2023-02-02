import random
import json
from urllib.request import urlopen
import bs4
import re
from scrape import read_jsonlines, jsonlines_path, OUT_DIR, jsonlines_to_csv
import time
import os
import shutil


SEED = 12345
N_SYNTH_PER_EXERCISE = 5
SLEEP_BETWEEN_CALLS = 1

def main():

    random.seed(SEED)

    os.makedirs(f'{OUT_DIR}/resynthesized', exist_ok=True)

    shutil.copyfile(jsonlines_path, jsonlines_path + '.resynth_backup')
    print('I made a backup of', jsonlines_path)

    items = read_jsonlines(jsonlines_path)

    with open(jsonlines_path, 'a') as json_writer:
        exercises = [item for item in items if item['type'] == 'exercise']
        for exercise in exercises:
            original_todi_parts = exercise['todi_sep'].split('|')
            for i, new_todi_parts in enumerate(random_todi_sequence(original_todi_parts, N_SYNTH_PER_EXERCISE)):
                resynthesize(exercise, new_todi_parts, str(i), json_writer)
                time.sleep(SLEEP_BETWEEN_CALLS)

    jsonlines_to_csv(jsonlines_path)


def resynthesize(exercise, todi_parts, suffix, json_writer):

    meta = {
        'type': 'synthetic',
        'index': f'{exercise["index"]}-{suffix}',
        'words': exercise['words'],
        'words_sep': exercise['words_sep'],
        'exercise_id': exercise['exercise_id'],
    }

    prefix, _ = exercise['exercise_id'].split('_')
    prefix = prefix[2:] # remove ex...
    uiting = exercise['index']

    meta['todi_sep'] = '|'.join(todi_parts)
    meta['todi'] = ' '.join(todi_parts)

    todi_string_for_url = " + ".join([t or '---' for t in todi_parts]).replace(' ', '%20')
    synthesis_url = f'https://todi.cls.ru.nl/cgi-bin/synthese{prefix}.pl?var=set&todi={uiting}={todi_string_for_url}'

    meta['page_url'] = synthesis_url
    print(synthesis_url)

    with urlopen(synthesis_url) as htmlreader:
        synthesis_page = bs4.BeautifulSoup(htmlreader, 'html.parser')

    sound_table = synthesis_page.find('tr', {'onclick': lambda x: x and x.startswith('play_sound')}, recursive=True)
    if sound_table:
        sound_match = re.search(r'\'(https://todi\.cls\.ru\.nl/PraatResynthese/\d+)\'', sound_table['onclick'])

        if sound_match:
            sound_url = sound_match.group(1) + '.wav'
            meta['sound_url'] = sound_url
            try:
                with urlopen(sound_url) as soundreader:
                    sound = soundreader.read()
                sound_file = f'resynthesized/{meta["index"]}.wav'
                meta['sound_file'] = sound_file
                with open(f'{OUT_DIR}/{sound_file}', 'wb') as soundwriter:
                    soundwriter.write(sound)
            except Exception as e:
                print(sound_url, e)

    image_button = synthesis_page.find('input', {'onclick': lambda x: x and x.startswith('PopUp2TextGrid')}, recursive=True)
    if image_button:
        image_match = re.search(r'https://todi\.cls\.ru\.nl/PraatResynthese/\d+\.png', image_button['onclick'])
        if image_match:
            image_url = image_match.group()
            meta['image_url'] = image_url
            try:
                with urlopen(image_url) as imagereader:
                    image = imagereader.read()
                image_filename = f'resynthesized/{meta["index"]}.png'
                meta['image_file'] = image_filename
                with open(f'{OUT_DIR}/{image_filename}', 'wb') as imagewriter:
                    imagewriter.write(image)
            except Exception as e:
                print(image_url, e)

    json_writer.write(json.dumps(meta) + '\n')



initial_boundaries = ['%H', '%L', '%HL']
initial_boundary_weights = [30, 50, 10]
final_boundaries = ['H%', 'L%', '%']
final_boundary_weights = [30, 50, 20]
accents = ['H*', 'L*', 'H*L','L*H', 'H*LH', 'L*HL', 'H*!H']
accent_weights = [200, 50, 200, 200, 30, 200, 20]
prob_downstep = .3

# accent weights very loosely based on frequencies copied from
# http://gep.ruhosting.nl/carlos/Hu_Janssen_Hansen_AASP_Hu_ToDI.pdf:
#     'H*': 187,
#     'L*': 44,
#     'L*H': 617,
#     'H*LH': 2,
#     '!H*L': 178,
#     '!H*': 34,
#     'L*HL': 794,

def random_todi_sequence(original_todi_parts, k):
    """
    Generates k random todi sequences from an original todi sequence (list of strings).
    It keeps all boundaries and accents in place, only randomly changes their tones.
    Generated sequences are different from the original and from each other.
    """
    todi_sequences_to_avoid_duplicates = {tuple(original_todi_parts)}
    n_attempts = 0

    while len(todi_sequences_to_avoid_duplicates) < k + 1 and n_attempts < k * 10:
        n_attempts += 1

        new_todi_parts = []
        can_downstep = False
        for i, p in enumerate(original_todi_parts):

            if '*' in p:
                if any('*' in q for q in original_todi_parts[i+1:]):
                    # H*!H only allowed as final accent
                    weights = accent_weights[:-1] + [0]
                else:
                    weights = accent_weights

                new_part = random.choices(accents, weights=weights)[0]
                if new_part.startswith('H'):
                    if can_downstep and random.random() < prob_downstep:
                        new_part = new_part.replace('H', '!H', 1)
                    # downstep only allowed after a first H accent
                    can_downstep = True

            elif p in initial_boundaries:
                new_part = random.choices(initial_boundaries, weights=initial_boundary_weights)[0]

            elif p in final_boundaries:
                new_part = random.choices(final_boundaries, weights=final_boundary_weights)[0]

            else:
                new_part = ''

            new_todi_parts.append(new_part)

        new_todi_parts_tuple = tuple(new_todi_parts)
        if new_todi_parts_tuple not in todi_sequences_to_avoid_duplicates:
            todi_sequences_to_avoid_duplicates.add(new_todi_parts_tuple)
            yield new_todi_parts


# This was a first attempt, keeping only the boundaries in place, but it is too random.
# def random_todi(original_todi_parts, k):
#     prob_accent = 0.4
#     prob_downstep = 0.5
#     prob_optional = 0
#
#     n_attempts = 0
#
#     while n_attempts < k:
#
#         if isinstance(original_todi_parts, list):
#             skeleton = ['' for _ in original_todi_parts]
#             for i, p in enumerate(original_todi_parts):
#                 if p in initial:
#                     skeleton[i] = random.choice(initial)
#                 elif p in final:
#                     skeleton[i] = random.choice(final)
#                 else:
#                     continue
#         else:
#             skeleton = ['' for _ in range(original_todi_parts)]
#             skeleton[0], skeleton[-1] = random.choice(initial), random.choice(final)
#
#         result = ['' for _ in skeleton]
#         can_downstep = False
#         can_accent = True
#         must_accent = False
#
#         for i, p in enumerate(skeleton):
#             if '%' in p:
#                 result[i] = p
#                 continue
#             if i == len(skeleton) - 2 and not any('*' in p for p in result):
#                 must_accent = True
#
#             if must_accent or (can_accent and random.random() < prob_accent):
#                 accent = random.choice(accents)
#                 if accent == 'H*!H':
#                     can_accent = False
#                 if can_downstep and random.random() < prob_downstep and accent.startswith('H'):
#                     accent = accent.replace('H', '!H', 1)
#                 if accent.startswith('H'):
#                     can_downstep = True
#                 if random.random() < prob_optional:
#                     accent = f'({accent})'
#                 result[i] = accent
#
#         n_attempts += 1
#         yield result


if __name__ == '__main__':
    main()