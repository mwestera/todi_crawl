# The unofficial, scraped ToDI dataset

This repository, specifically the folder [scraped](scraped), contains a dataset of Dutch audio with intonation transcriptions, scraped from the ToDI website on February 1 2023: https://todi.cls.ru.nl/ToDI/home.htm

It also contains the scripts used for the aforementioned scraping. These were very quickly written and intended for my personal, one-time use, so use at your own risk. 💥 

## Index

A full index of all `.wav` files with some meta-data, and transcriptions where available, is given in [index.csv](scraped/index.csv) (or, same information but different format, [index.jsonlines](scraped/index.jsonlines)). A small number of files (`.wav` or associated `.png` or `.gif`) may be missing, for instance due to broken links on the ToDI website itself. In that case, the corresponding rows in the [index.csv](scraped/index.csv) file will have empty fields `image_file` and/or `sound_file`. 

The best approach to access these data is probably to start from [index.csv](scraped/index.csv) and select the rows of interest (e.g., only rows with `todi_sep` transcriptions), then collect or process the file from the `sound_file` column.

## Recreating the dataset

The full procedure to create this dataset is to first run `scrape.py`, then run `ocr.py` to extract (imperfect) transcriptions from the `.gif` files where needed (see below for explanation), and finally run `resynthesize.py` to add synthesized examples (see also below). Each of these scripts will also update the files [index.csv](scraped/index.csv) and [index.jsonlines](scraped/index.jsonlines).

## Types of data

The dataset has three types of data (the `type` column in the [index.csv](index.csv) file. These correspond to three different ways in which the ToDI website provides access to data. The three types of data are stored in separate subfolders in [scraped](scraped):


### 1. [Examples](scraped/examples)
These `.wav` files have an accompanying words transcription and ToDI-transcription in a .gif file. I used automatic 'optical character recognition' (see [ocr.py](ocr.py)) to extract the words and ToDI tones from these .gif files, but this is imperfect, and also words and tones are not aligned. You find these in the `words_ocr` and `todi_ocr` columns in the file [index.csv](scraped/index.csv). It should be fairly quick to go through the `.gif` files manually and correct these transcriptions. 

### 2. [Exercises](scraped/exercises)
These `.wav` files came with the correct word and ToDI transcriptions (as well as with a `.png` image of the pitch contour). You find these in the `words` and `todi` columns of [index.csv](scraped/index.csv). The transcriptions are also aligned (i.e., words with tones), which you find in the `words_sep` and `todi_sep` columns, with vertical bars `|` as separators. 

### 3. [Resynthesized](scraped/resynthesized)
These `.wav` files were synthetically generated from the aforementioned exercise files by replacing the fundamental frequency. This was done by interfacing with a script on the ToDI website (but I could not access the script itself). These synthetic variants come with correct, aligned word and ToDI transcriptions just like the original exercise files (as well as a `.png` image of the resulting, synthetic pitch contour). 

More precisely, for each original exercise `.wav` file I randomly generated 5 new variants by replacing boundary tones and accents (but keeping them in their original locations): see the function `random_todi_sequence` in [resynthesize.py](resynthesize.py). It can be probably be refined, and the sampling probabilities of the different accents etc. tweaked, but this will do for now.

