import re
import time
import json

raw_instruction = """ You are given a japanese subtitle file. 
                  You translate every word into english and give its definitions in brackets right after.
                  Some words and names can be skipped with _. Don't translate what is in brackets.
              """

instruction = re.sub(' {2,}', ' ', raw_instruction.replace('\n', ' ').strip())


def load_api_key():
    with open('api/api_key.txt', 'r') as file:
        api_key = file.read().strip()
    return api_key


def get_latest_model(client):
    fine_tune_jobs = client.fine_tuning.jobs.list()
    fine_tune_jobs.data.sort(key=lambda x: x.created_at, reverse=True)

    fine_tuned_model = None
    for job in fine_tune_jobs.data:
        fine_tuned_model = job.fine_tuned_model
        if fine_tuned_model is not None:
            break
    print('Retrieved model name: ' + fine_tuned_model)
    return fine_tuned_model


def remove_brackets(text):
    modified_text = re.sub(r'(\(.*?\)|（.*?）|\{.*?\})', '', text)

    if re.search(r'\S', modified_text):
        return modified_text.strip()
    else:
        return text


def prepare_requests(srt_text, client):
    requests = []
    model = get_latest_model(client)
    for i, text in enumerate(srt_text):
        clean_text = remove_brackets(text)
        request = {
            "custom_id": f"request-{i+1}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": clean_text}
                ],
                "max_tokens": 1000
            }
        }
        requests.append(request)

    return requests


def batch_query_chatgpt(client):
    batch_input_file = client.files.create(
      file=open("batch.jsonl", "rb"),
      purpose="batch"
    )
    batch_input_file_id = batch_input_file.id
    response = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
          "description": "Annotate Subtitles"
        }
    )
    return response.id


def retrieve_batch(client, batch_id):
    while True:
        batch = client.batches.retrieve(batch_id)

        if batch.status == 'completed':
            print("Batch completed. Retrieving content...")
            binary_content = b""
            for chunk in client.files.content(batch.output_file_id).iter_bytes():
                binary_content += chunk

            jsonl_content = binary_content.decode('utf-8')
            json_objects = []
            for line in jsonl_content.strip().split('\n'):
                if line.strip():
                    json_objects.append(json.loads(line))

            json_objects.sort(key=lambda obj: int(obj['custom_id'].split('-')[1]))
            sorted_jsonl_content = '\n'.join(json.dumps(obj) for obj in json_objects)

            return sorted_jsonl_content

        elif batch.status == 'expired' or batch.status == 'failed' or batch.status == 'cancelled':
            print("Batch Failed")
            return
        else:
            print("Batch not completed yet. Checking again in 1 second...")

        time.sleep(1)