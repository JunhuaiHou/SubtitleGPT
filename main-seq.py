from openai import OpenAI
from api.gpt_client import load_api_key, query_chatgpt, get_latest_model
import time
import os
import json


def find_srt_file():
    for file_name in os.listdir('./subtitles'):
        if file_name.lower().endswith('.srt'):
            return os.path.join('subtitles', file_name)
    return None


def load_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    text = []
    current_subtitle = []
    previous_line_was_timestamp = False

    for line in lines:
        line_content = line.strip()

        if line_content.isdigit():
            if current_subtitle:
                text.append(' '.join(current_subtitle))
                current_subtitle = []
            previous_line_was_timestamp = False
            continue

        if '-->' in line_content:
            previous_line_was_timestamp = True
            continue

        if line_content:
            current_subtitle.append(line_content)
            previous_line_was_timestamp = False
        else:
            if previous_line_was_timestamp:
                current_subtitle.append('♬～')
                previous_line_was_timestamp = False

    if current_subtitle:
        text.append(' '.join(current_subtitle))

    return text


def load_full_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    text = []
    current_subtitle = []
    for line in lines:
        line_content = line.strip()

        if line_content.isdigit() and current_subtitle:
            text.append('\n'.join(current_subtitle))
            current_subtitle = [line_content]
        else:
            current_subtitle.append(line_content)

    if current_subtitle:
        text.append('\n'.join(current_subtitle))

    return text


def write_requests_to_file(requests, filename):
    print('Creating batch file.')
    with open(filename, 'w') as f:
        for request in requests:
            f.write(json.dumps(request) + '\n')


def get_responses(client, subtitles):
    start_time = time.time()
    gpt_responses = []
    model = get_latest_model(client)
    total_subtitles = len(subtitles)

    for idx, subtitle in enumerate(subtitles, start=1):
        response = query_chatgpt(client, subtitle, model)
        content = response.choices[0].message.content
        gpt_responses.append(content)
        print(f'Request completed for subtitle {idx}/{total_subtitles}.')

    end_time = time.time()
    duration = end_time - start_time
    minutes, seconds = divmod(duration, 60)
    print(f'Generation Successful. Duration: {int(minutes)} minutes {seconds:.2f} seconds')
    return gpt_responses


def create_new_srt(input_file_path, output_file_path, gpt_responses):
    print('Creating new subtitle file.')
    srt_contents = load_full_srt(input_file_path)
    new_srt_content = []

    counter = 1

    for original, response in zip(srt_contents, gpt_responses):
        first_two_lines, remaining_lines = original.split('\n', 2)[:2], original.split('\n', 2)[2:]
        if not response.endswith('\n'):
            response += '\n'

        new_srt_content.append('\n'.join(first_two_lines) + '\n' + f'{counter}_ {response}')
        counter += 1
    with open(output_file_path, 'w', encoding='utf-8-sig') as file:
        file.write('\n'.join(new_srt_content))
    print('New subtitle file Created.')


if __name__ == '__main__':
    debug = False

    if debug:
        api_key = 'invalid_key'
    else:
        api_key = load_api_key()

    client = OpenAI(api_key=api_key)
    srt_file_path = find_srt_file()
    if srt_file_path:
        subtitles = load_srt(srt_file_path)
        print('Loaded subtitles.')
        responses = get_responses(client, subtitles)
        create_new_srt(srt_file_path, 'subtitles/znew_subtitle.srt', responses)
    else:
        print("No SRT file found in the current directory.")