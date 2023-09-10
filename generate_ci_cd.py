import os
import openai
import json
import logging
from git import Repo
import argparse

logging.basicConfig(level=logging.INFO)

def ensure_directory(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    logging.info(f"Ensured directory for {file_path}.")

def openai_call(prompt, model_name, max_tokens=300, role="user"):
    messages = [
        {"role": "system", "content": "You are a script that helps set up a Repository with initial files."},
        {"role": role, "content": prompt}
    ]
    response = openai.ChatCompletion.create(model=model_name, messages=messages, max_tokens=max_tokens)
    logging.info("Retrieved result:\n%s", response)
    message_content = response.choices[0].message['content'].strip()
    logging.info("Returning message:\n%s", message_content)
    return message_content

def generate_ci_cd(branch_name, keywords, openai_token, model_name):
    openai.api_key = openai_token

    prompt_for_files = f"List the files and their specific directories and requirements for a CI/CD setup with the following keywords: {keywords}. Provide the information as a compact, JSON-formatted dictionary where the keys are file paths (not directories, just paths!) and the values are lists of keywords. Make sure the output is parseable by Python's json.loads."
    files_and_requirements = json.loads(openai_call(prompt_for_files, model_name))
    logging.info(f"Generated file and directory requirements: {files_and_requirements}")

    repo = Repo('.')

    remote_url = repo.remotes.origin.url
    new_url = remote_url.replace("https://", f"https://{os.getenv('GITHUB_TOKEN')}:x-oauth-basic@")
    repo.remotes.origin.set_url(new_url)

    logging.info("Remote URL set to: %s", repo.remotes.origin.url)


    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    logging.info(f"Checked out new branch: {branch_name}")

    for file_path, file_keywords in files_and_requirements.items():
        ensure_directory(file_path)

        prompt_for_content = f"Generate content for {file_path} with the following keywords: {file_keywords}."
        file_content = openai_call(prompt_for_content, model_name)
        logging.info(f"Generated content for {file_path}.")

        with open(file_path, "w") as f:
            f.write(file_content)
    
    repo.git.add(all=True)
    repo.index.commit("Add generated CI/CD setup")
    repo.git.push("origin", branch_name)
    logging.info(f"Committed and pushed changes to {branch_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CI/CD setup.")
    parser.add_argument('--branch_name', default="ci-cd-setup", help="Name of the new branch.")
    parser.add_argument('--keywords', required=True, help="Keywords to inform the setup.")
    parser.add_argument('--openai_token', required=True, help="OpenAI API Token.")
    parser.add_argument('--model_name', default="gpt-3.5-turbo-16k-0613", help="OpenAI model name.")
    
    args = parser.parse_args()
    generate_ci_cd(args.branch_name, args.keywords, args.openai_token, args.model_name)
