import sys
import random
import numpy as np
import sounddevice
import wave
import json
import os
import shutil
from pydub import AudioSegment
from scipy.signal import lfilter
import boto3

## todo: create env with frequency and spaces keys

DO_SPACES_ACCESS_KEY = 'DO00222U287G6HWUQYGH'
DO_SPACES_SECRET_KEY = 'Wm7n3fC0laQ58q/0Odu0I3CFhfXf8Q2tDqFibPVT5O4'
DO_SPACES_BUCKET_NAME = 'soffia'
DO_SPACES_ENDPOINT_URL = 'https://nyc3.digitaloceanspaces.com'

file_format = sys.argv[1]
repeat_option_times = sys.argv[2]

data_frequency = {
    '1': [19000, 19250],
    '2': [19000, 19300],
    '3': [19000, 19350],
    'a': [19000, 19406],
    '4': [19070, 19280],
    '5': [19070, 19330],
    '6': [19070, 19380],
    'b': [19070, 19396],
    '7': [19140, 19350],
    '8': [19140, 19400],
    '9': [19140, 19450],
    'c': [19140, 19506],
    '*': [19210, 19390],
    '0': [19210, 19440],
    '#': [19210, 19490],
    'd': [19210, 19546]
}


def gera_id():
    numeros = list(range(10, 10000))
    id = ''

    while len(id) < 8:
        numero = random.choice(numeros)

        if len(id) == 0 and numero < 1000:
            continue

        id += str(numero)
        numeros.remove(numero)

    id = 'AB' + id + 'CD'

    return id


def verifica_existencia(id):
    with open('ids.json', 'r') as arquivo:
        ids = json.load(arquivo)
        if id in ids:
            return True
    return False

def gravar_id(id):
    with open('ids.json', 'r+') as arquivo:
        ids = json.load(arquivo)
        ids.append(id)
        arquivo.seek(0)
        json.dump(ids, arquivo, indent=4)
        arquivo.truncate()

def gerar_id_unico():
    while True:
        novo_id = gera_id()

        if not verifica_existencia(novo_id) and not tem_numeros_iguais_lado_a_lado(novo_id):
            gravar_id(novo_id)
            return novo_id

def tem_numeros_iguais_lado_a_lado(id):
    for i in range(len(id) - 1):
        if id[i] == id[i + 1]:
            return True
    return False

def generate_tone(frequency, duration, sample_rate, amplitude):
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    samples = amplitude * np.sin(2 * np.pi * frequency * t)
    return samples

def apply_preemphasis_filter(samples, alpha=1):
    return lfilter([1, -alpha], 1, samples)

def play_frequencies(frequencies, sample_rate, play_sound=True, save_to_file=False, file_name=None, file_format='wav'):

    duration = 0.5
    amplitude = 0.5

    combined_tone = np.array([])

    for frequency in frequencies:
        tone = generate_tone(frequency, duration, sample_rate, amplitude)
        combined_tone = np.concatenate((combined_tone, tone))

    if save_to_file:
        if file_format == 'mp3':
            combined_tone = apply_preemphasis_filter(combined_tone)

        int_samples = (combined_tone * 32767).astype(np.int16)

        if file_format == 'wav':
            with wave.open(file_name, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(int_samples.tobytes())

        elif file_format == 'mp3':
            audio_segment = AudioSegment(
                int_samples.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=1
            )
            audio_segment.export(file_name, format='mp3', bitrate="128k" , parameters=["-ar", "48000"])

    if play_sound:
        sounddevice.play(combined_tone, sample_rate)
        sounddevice.wait()



def upload_to_digital_ocean(file_name, local_path):
    session = boto3.session.Session()
    client = session.client('s3',
                           endpoint_url=DO_SPACES_ENDPOINT_URL,
                           aws_access_key_id=DO_SPACES_ACCESS_KEY,
                           aws_secret_access_key=DO_SPACES_SECRET_KEY)

    try:
        with open(local_path, 'rb') as data:
            client.upload_fileobj(data, DO_SPACES_BUCKET_NAME, file_name)
    except Exception as e:
        print("error")

def main():

    frequency_table = data_frequency

    chave = gerar_id_unico()

    frequencies = []

    for letter in chave:
        if letter.lower() in frequency_table:
            frequencies.extend(frequency_table[letter.lower()])

    if frequencies:

        sample_rate = 44100
        file_name = chave

        play_option = 'n'
        file_name += "." + file_format


        ##todo: get dynamic amount options
        repeat_option = int(repeat_option_times)

        total_duration = repeat_option * 0.4 * len(chave)

        play_frequencies(frequencies * repeat_option, sample_rate, play_sound=(play_option.lower() == 's'), save_to_file=True,
                            file_name=file_name, file_format=file_format)

        shutil.move(file_name, '../audios/' + file_name)
        dest_path = "../audios/" + file_name
        os.chmod(dest_path, 0o755)
        upload_to_digital_ocean(file_name, dest_path)
        print(file_name)

    else:
        print(False)


if __name__ == '__main__':
    main()
