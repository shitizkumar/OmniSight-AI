
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from github import Auth, Github

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

REPOSITORY = "shitizkumar/OmniSight-AI"
ALLOWED_FILES = {"mock-store/src/App.css"}


def create_pull_request(
    file_path: str,
    commit_message: str,
    pr_title: str,
    pr_body: str,
    verification_passed: bool = False,
) -> str:
    if not verification_passed:
        raise RuntimeError("Repair verification has not passed.")

    if file_path not in ALLOWED_FILES:
        raise ValueError("File is not approved for automated commits.")

    if not re.fullmatch(r"[a-zA-Z0-9._/-]+", file_path):
        raise ValueError("Invalid file path.")

    local_file = ROOT_DIR / file_path

    if not local_file.is_file():
        raise FileNotFoundError(file_path)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is missing.")

    github = Github(auth=Auth.Token(token))

    try:
        repo = github.get_repo(REPOSITORY)
        main = repo.get_branch("main")

        branch_name = f"omnisight/repair-{os.urandom(4).hex()}"

        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=main.commit.sha,
        )

        remote_file = repo.get_contents(file_path, ref=branch_name)
        content = local_file.read_text(encoding="utf-8")

        if remote_file.decoded_content.decode("utf-8") == content:
            raise RuntimeError("No source changes to commit.")

        repo.update_file(
            path=file_path,
            message=commit_message,
            content=content,
            sha=remote_file.sha,
            branch=branch_name,
        )

        pull = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base="main",
        )

        return pull.html_url

    finally:
        github.close()
