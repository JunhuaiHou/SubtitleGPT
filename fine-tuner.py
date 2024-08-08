import yaml
import json
from openai import OpenAI
from api.gpt_client import instruction, load_api_key, get_latest_model, gpt_name


def format_data(prompt, answer):
    return {
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer}
        ]
    }


def save_data(translation_pairs, file_path):
    with open(file_path, 'w') as file:
        for index, (question, answer) in enumerate(translation_pairs):
            formatted_translation = format_data(question, answer)
            json.dump(formatted_translation, file)
            file.write('\n')


def extract_training_pairs(file_path):
    translation_pairs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            loaded_pairs = yaml.safe_load(file)

            for pair in loaded_pairs:
                japanese = pair.get('prompt', 'Prompt not found')
                english = pair.get('answer', 'Answer not found')

                translation_pairs.append((japanese, english))
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file: {exc}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return translation_pairs


def archive_file(src, dst):
    with open(src, 'r', encoding='utf-8') as src_file:
        src_contents = src_file.read()

    while src_contents.endswith('\n'):
        src_contents = src_contents.rstrip()

    with open(dst, 'a', encoding='utf-8') as dst_file:
        dst_file.write("\n\n" + src_contents)


def rewrite_template(src, dst):
    with open(src, 'r', encoding='utf-8') as src_file:
        src_contents = src_file.read()

    while src_contents.endswith('\n'):
        src_contents = src_contents.rstrip()

    with open(dst, 'w', encoding='utf-8') as dst_file:
        dst_file.write(src_contents)


def fine_tune():
    api_key = load_api_key()
    client = OpenAI(api_key=api_key)

    training_file = client.files.create(
      file=open(training_data, "rb"),
      purpose="fine-tune"
    )

    client.fine_tuning.jobs.create(
      training_file=training_file.id,
      model=get_latest_model(client),
      hyperparameters={
        "n_epochs": 5,
        "batch_size": 1,
        "learning_rate_multiplier": 2
      },
      suffix=gpt_name,
    )


training_translation = 'data/training_translation.yaml'
archive_path = 'data/archive/training_archive.yaml'
training_data = 'data/training_data.jsonl'
template_path = 'data/archive/template.yaml'

training_pairs = extract_training_pairs(training_translation)
save_data(training_pairs, training_data)

fine_tune()

archive_file(training_translation, archive_path)
rewrite_template(template_path, training_translation)

