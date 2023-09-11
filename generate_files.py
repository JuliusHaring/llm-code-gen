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
            if os.path.isdir(key):
                logging.error(f"The key {key} is a directory.")
                return False, None
        return True, parsed_output
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON.")
        return False, None


def openai_call(prompt, model_name, max_tokens=300, role="user"):
    messages = [
        {
            "role": "system",
            "content": "You are a script that helps set up a Repository with initial files.",
        },
        {"role": role, "content": prompt},
    ]
    response = openai.ChatCompletion.create(
        model=model_name, messages=messages, max_tokens=max_tokens
    )
    logging.info("Retrieved result:\n%s", response)
    message_content = response.choices[0].message["content"].strip()
    logging.info("Returning message:\n%s", message_content)
    return message_content


def generate_files(
    branch_name: str,
    descriptions: str,
    openai_token: str,
    model_name: str,
    max_tokens: int,
    force_push: bool,
    max_retries: int = 3,
):
    openai.api_key = openai_token
    is_valid = False
    retries = 0

    while not is_valid and retries < max_retries:
        prompt_for_files = (
            "List the files and their specific directories and requirements for a"
            f"production ready codebase using the following descriptions: {descriptions}."
            "Provide the information as a compact, JSON-formatted dictionary where the keys are file paths"
            "(not directories, just paths!) and the values are the descriptions strings."
            "Make sure the output is parseable by Python's json.loads."
        )

        raw_output = openai_call(
            prompt=prompt_for_files, model_name=model_name, max_tokens=max_tokens
        )

        is_valid, files_and_requirements = validate_dict_output(raw_output)

        if not is_valid:
            retries += 1
            logging.warning(
                f"Invalid output received. Retrying {retries}/{max_retries}"
            )

    if is_valid:
        files_and_requirements = json.loads(raw_output)
        logging.info(
            f"Generated file and directory requirements: {files_and_requirements}"
        )

        repo = Repo(".")

        remote_url = repo.remotes.origin.url
        new_url = remote_url.replace(
            "https://", f"https://{os.getenv('GITHUB_TOKEN')}:x-oauth-basic@"
        )
        repo.remotes.origin.set_url(new_url)

        logging.info("Remote URL set to: %s", repo.remotes.origin.url)

        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        logging.info(f"Checked out new branch: {branch_name}")

        for file_path, file_descriptions in files_and_requirements.items():
            if os.path.exists(file_path):
                logging.warning(f"File {file_path} already exists. Skipping.")
                continue

            ensure_directory(file_path)

            prompt_for_content = (
                "Here is a list of all files to be generated and their requirements:"
                f" {json.dumps(files_and_requirements)}."
                f"Create the file content of '{file_path}' from the following description: {file_descriptions}. "
                "Only output the content for this specific file."
                "Your output will be directly copied to the file, so you will output proper content,"
                "no comments about it."
            )

            file_content = openai_call(
                prompt=prompt_for_content, model_name=model_name, max_tokens=max_tokens
            )
            logging.info(f"Generated content for {file_path}.")

            with open(file_path, "w") as f:
                f.write(file_content)

        repo.git.add(all=True)
        repo.index.commit("Add generated CI/CD setup")
        if force_push:
            repo.git.push("origin", branch_name, "--force")
        else:
            repo.git.push("origin", branch_name)
        logging.info(f"Committed and pushed changes to {branch_name}")
    else:
        logging.error("Max retries reached.")
        raise ValueError


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate code using OpenAI API.")
    parser.add_argument(
        "--branch_name", default="ci-cd-setup", help="Name of the new branch."
    )
    parser.add_argument(
        "--descriptions", required=True, help="Descriptions to inform the setup."
    )
    parser.add_argument("--openai_token", required=True, help="OpenAI API Token.")
    parser.add_argument(
        "--model_name", default="gpt-3.5-turbo-16k-0613", help="OpenAI model name."
    )
    parser.add_argument(
        "--max_tokens", default=300, type=int, help="Max tokens for OpenAI API call."
    )
    parser.add_argument(
        "--log_level", default="INFO", type=str, help="Set the log level."
    )
    parser.add_argument(
        "--force_push",
        action="store_true",
        help="Enable force push to the remote branch.",
        default=True,
    )

    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    generate_files(
        branch_name=args.branch_name,
        descriptions=args.descriptions,
        openai_token=args.openai_token,
        model_name=args.model_name,
        max_tokens=args.max_tokens,
        force_push=args.force_push,
    )
