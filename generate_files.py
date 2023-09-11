import argparse
import json
import logging
import os

import openai
from git import Repo


def ensure_directory(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    logging.info(f"Ensured directory for {file_path}.")


def validate_dict_output(raw_output):
    try:
        parsed_output = json.loads(raw_output)
        if not isinstance(parsed_output, dict):
            logging.error("Output is not a dictionary.")
            return False, None
        for key, value in parsed_output.items():
            if not isinstance(key, str) or not isinstance(value, str):
                logging.error(
                    "Dictionary keys and/or values are not strings: %s, %s.",
                    str(key),
                    str(value),
                )
                return False, None
        return True, parsed_output
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON.")
        return False, None


def openai_call(prompt, model_name, max_tokens=300):
    messages = [
        {
            "role": "system",
            "content": "You are a script that helps set up a Repository with initial files.",
        },
        {"role": "user", "content": prompt},
    ]
    response = openai.ChatCompletion.create(
        model=model_name, messages=messages, max_tokens=max_tokens
    )
    logging.info(f"Retrieved result:\n{response}")
    return response.choices[0].message["content"].strip()


def get_file_requirements_dict(descriptions, model_name, max_tokens):
    prompt_for_files = (
        "List the files and their specific directories and requirements for a"
        f"production ready codebase using the following descriptions: '{descriptions}'."
        "Stick to that description, don't add anything else. Use the minimum amount of required files."
        "Make the minimum amount of assumptions about the rest of the repo."
        "Provide the information as a compact, JSON-formatted dictionary where the keys are file paths"
        "(not directories, just paths!) and the values are the descriptions strings."
    )
    raw_output = openai_call(prompt_for_files, model_name, max_tokens)
    is_valid, files_and_requirements = validate_dict_output(raw_output)
    if is_valid:
        logging.info(
            f"Generated file and directory requirements: {files_and_requirements}"
        )
    return is_valid, files_and_requirements


def get_file_content(
    file_path, file_descriptions, files_and_requirements, model_name, max_tokens
):
    prompt_for_content = (
        "Here is a list of all files to be generated and their requirements:"
        f" {json.dumps(files_and_requirements)}."
        f"Create the file content of '{file_path}' from the following description: {file_descriptions}. "
        "Only output the content for this specific file."
        "Your output will be directly copied to the file, so you will output proper content,"
        "no comments about it."
    )
    file_content = openai_call(prompt_for_content, model_name, max_tokens)
    logging.info(f"Generated content for {file_path}.")
    return file_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate code using OpenAI API.")
    parser.add_argument("--branch_name", default="llm-generated-code")
    parser.add_argument("--commit_message", default="feat: add llm-generated code")
    parser.add_argument("--descriptions", required=True)
    parser.add_argument("--openai_token", required=True)
    parser.add_argument("--model_name", default="gpt-3.5-turbo-16k-0613")
    parser.add_argument("--max_tokens", default=300, type=int)
    parser.add_argument("--log_level", default="INFO", type=str)
    parser.add_argument("--force_push", action="store_true", default=True)

    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    openai.api_key = args.openai_token

    repo = Repo(".")
    repo.create_head(args.branch_name).checkout()

    is_valid, files_and_requirements = get_file_requirements_dict(
        args.descriptions, args.model_name, args.max_tokens
    )

    if not is_valid:
        logging.error("Invalid file requirements dictionary. Exiting.")
        exit(1)

    for file_path, file_descriptions in files_and_requirements.items():
        if os.path.exists(file_path):
            logging.warning(f"File {file_path} already exists. Skipping.")
            continue

        ensure_directory(file_path)
        file_content = get_file_content(
            file_path,
            file_descriptions,
            files_and_requirements,
            args.model_name,
            args.max_tokens,
        )

        with open(file_path, "w") as f:
            f.write(file_content)

    repo.git.add(all=True)
    repo.index.commit(args.commit_message)
    repo.git.push("origin", args.branch_name, "--force" if args.force_push else "")
