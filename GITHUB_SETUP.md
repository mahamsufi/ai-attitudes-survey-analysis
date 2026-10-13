# Publish the project on GitHub

Repository: https://github.com/mahamsufi/ai-attitudes-survey-analysis

The project was prepared locally and uploaded through GitHub’s browser interface. The instructions below explain how to maintain a local Git checkout.

## Account

Use your existing GitHub account and authenticate through GitHub's normal sign-in flow. Do not put credentials in this repository.

Suggested profile description:

> Social researcher working on AI perceptions, trust and responsible technology. Developing Python skills through transparent, reproducible analysis projects.

This is suggested wording only; the profile has not been edited.

## Repository

Repository name: `ai-attitudes-survey-analysis`

Repository description: `Python analysis of UK public attitudes to AI using public CDEI survey data.`

For a new copy, create an empty repository under your own account. Upload only the files in this project, including the generated aggregate outputs. Exclude `.venv`, `.cache`, raw downloads and any other personal files. The supplied `.gitignore` handles those exclusions when using Git.

After configuring Git with your chosen public identity, the usual commands from this folder are:

```bash
git init -b main
git add .
git diff --cached --stat
git commit -m "Add public attitudes survey analysis project"
git remote add origin https://github.com/YOUR_USERNAME/ai-attitudes-survey-analysis.git
git push -u origin main
```

Replace `YOUR_USERNAME` with the actual account name. Authenticate through GitHub's normal flow; do not paste a token into a script or remote URL. Review the staged file list before committing.

The standalone ZIP provided with this project contains the publishable files. Extract it before using GitHub's upload-files interface; uploading only a ZIP would hide the code and README from normal browsing.
