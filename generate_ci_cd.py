import os
import openai
import json
from git import Repo
import argparse

def ensure_directory(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def generate_ci_cd(branch_name, keywords, openai_token, model_name):
    openai.api_key = openai_token

    # Explicit prompt for file paths
    prompt_for_files = f"List the files and their specific directories and requirements for a CI/CD setup with the following keywords: {keywords}. Provide the information as a JSON-formatted dictionary."
    response_for_files = openai.Completion.create(model=model_name, prompt=prompt_for_files, max_tokens=100)
    
    files_and_requirements = json.loads(response_for_files.choices[0].text.strip())

    # Create and switch to new branch
    repo = Repo('.')
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()

    for file_path, file_keywords in files_and_requirements.items():
        # Make sure directory exists
        ensure_directory(file_path)

        # Generate content for each file
        prompt_for_content = f"Generate content for {file_path} with the following keywords: {file_keywords}."
        response_for_content = openai.Completion.create(model=model_name, prompt=prompt_for_content, max_tokens=300)
        
        file_content = response_for_content.choices[0].text.strip()

        with open(file_path, "w") as f:
            f.write(file_content)
    
    # Commit and push changes
    repo.git.add(all=True)
    repo.index.commit("Add generated CI/CD setup")
    repo.git.push("origin", branch_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CI/CD setup.")
    parser.add_argument('--branch_name', default="ci-cd-setup", help="Name of the new branch.")
    parser.add_argument('--keywords', required=True, help="Keywords to inform the setup.")
    parser.add_argument('--openai_token', required=True, help="OpenAI API Token.")
    parser.add_argument('--model_name', default="text-davinci-004", help="OpenAI model name.")
    
    args = parser.parse_args()
    generate_ci_cd(args.branch_name, args.keywords, args.openai_token, args.model_name)
