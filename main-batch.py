from openai import OpenAI
from api.gpt_client import prepare_batch_requests, load_api_key, batch_query_chatgpt, retrieve_batch, gpt_name
import time
import os
import json


def find_srt_file():
    srt_files = os.listdir('./subtitles')

    for file_name in srt_files:
        if file_name.lower().endswith('.srt') and not file_name.startswith(f'{gpt_name}_'):
            gpt_file_name = f'{gpt_name}_{file_name}'
            if gpt_file_name not in srt_files:
                return file_name
    return None


def load_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    text = []
    current_subtitle = []
    previous_line_was_timestamp = False

    for line in lines:
        line_content = line.strip()

        if line_content.startswith('\ufeff'):
            line_content = line_content[1:]

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
        if line_content.startswith('\ufeff'):
            line_content = line_content[1:]

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


def get_responses(client, srt_text):
    start_time = time.time()
    print('Preparing requests.')
    requests = prepare_batch_requests(srt_text, client)
    print('Requests prepared.')
    write_requests_to_file(requests, 'batch.jsonl')
    print('Batch file created.')
    id = batch_query_chatgpt(client)
    print('Batch file uploaded to OpenAI server.')
    batch_response = retrieve_batch(client, id)
    responses = []
    for line in batch_response.strip().split('\n'):
        if line.strip():
            data = json.loads(line)
            content = data['response']['body']['choices'][0]['message']['content']
            responses.append(content)

    end_time = time.time()
    duration = end_time - start_time
    minutes, seconds = divmod(duration, 60)
    print(f'Generation Successful. Duration: {int(minutes)} minutes {seconds:.2f} seconds')
    return responses


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
    srt_file_name = find_srt_file()
    srt_file_path = os.path.join('subtitles', srt_file_name)
    if srt_file_path:
        srt_text = load_srt(srt_file_path)
        print(f'Loaded subtitle file name {srt_file_name}')
        responses = get_responses(client, srt_text)
        create_new_srt(srt_file_path, f'subtitles/{gpt_name}_{srt_file_name}', responses)
    else:
        print("No SRT file found in the current directory.")
