# OpenAI Code Generator GitHub Action 🚀

## Overview 📖
This GitHub Action allows you to generate code files using the OpenAI API. It's perfect for automating the process of file generation and directly integrating these files into your codebase. After generation, it commits the files and optionally opens a pull request.

## Features 🌟
 - Code Generation: Generates files based on given descriptions.
 - Commit & Push: Commits the generated files and pushes to a new or existing branch.
 - Pull Requests: Optionally creates a pull request against a base branch.
 - Dry Run: Test the workflow without making any changes to the repo.

## Usage 🛠️
Include the action in your GitHub Actions workflow YAML:

```yaml
- name: OpenAI Code Generator
  uses: https://github.com/JuliusHaring/llm-code-gen@main
  with:
    descriptions: 'python linting with flake8 and github actions'
    openai_token: ${{ secrets.OPENAI_TOKEN }}
```


## Contributions 🤝
Feel free to open an issue or submit a pull request if you want to contribute.

## License 📝
This project is licensed under the MIT License. See the LICENSE file for details.

Enjoy using the OpenAI Code Generator GitHub Action! 🎉