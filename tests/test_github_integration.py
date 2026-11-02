
import json

import pytest

from github_integration import pull_request


def create_valid_report():
    return {
        "verification_method": "playwright_browser",
        "overall_status": "passed",
        "viewports": {
            name: {
                "status": "passed",
                "checks": {
                    "http_ok": True,
                    "heading_visible": True,
                    "checkout_form_visible": True,
                    "required_fields_present": True,
                    "submit_button_visible": True,
                    "no_horizontal_overflow": True,
                    "no_browser_errors": True,
                    **(
                        {"checkout_submission": True}
                        if name == "mobile"
                        else {}
                    ),
                },
                "browser_errors": [],
            }
            for name in ("mobile_small", "mobile", "tablet", "desktop")
        },
    }


class FakeGitHub:
    def __init__(self, auth):
        self.closed = False
        self.repo = FakeRepository()

    def get_repo(self, name):
        return self.repo

    def close(self):
        self.closed = True


class FakeRepository:
    def __init__(self):
        self.branch_created = False
        self.file_updated = False
        self.pull_created = False

    def get_branch(self, name):
        return type(
            "Branch",
            (),
            {"commit": type("Commit", (), {"sha": "main-sha"})()},
        )()

    def get_contents(self, path, ref):
        return type(
            "RemoteFile",
            (),
            {
                "sha": "file-sha",
                "decoded_content": b"old content",
            },
        )()

    def create_git_ref(self, ref, sha):
        self.branch_created = True

    def update_file(self, **kwargs):
        self.file_updated = True

    def create_pull(self, **kwargs):
        self.pull_created = True
        return type(
            "PullRequest",
            (),
            {"html_url": "https://github.com/example/pull/1"},
        )()


@pytest.fixture
def setup_pr_environment(monkeypatch, tmp_path):
    project_root = tmp_path
    source_file = project_root / "mock-store" / "src" / "App.css"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("new CSS content", encoding="utf-8")

    report_path = project_root / "artifacts" / "browser_verification_report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        json.dumps(create_valid_report()),
        encoding="utf-8",
    )

    monkeypatch.setattr(pull_request, "ROOT_DIR", project_root)
    monkeypatch.setattr(pull_request, "REPORT_PATH", report_path)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    fake_github = FakeGitHub(auth=None)
    monkeypatch.setattr(
        pull_request,
        "Github",
        lambda auth: fake_github,
    )

    return fake_github, report_path


def test_valid_report_allows_pull_request(setup_pr_environment):
    fake_github, _ = setup_pr_environment

    url = pull_request.create_pull_request(
        "mock-store/src/App.css",
        "Update CSS",
        "UI repair",
        "Browser verification passed.",
    )

    assert url == "https://github.com/example/pull/1"
    assert fake_github.repo.branch_created is True
    assert fake_github.repo.file_updated is True
    assert fake_github.repo.pull_created is True
    assert fake_github.closed is True


@pytest.mark.parametrize(
    "report_change, error_message",
    [
        (lambda report: report.update(overall_status="failed"), "did not pass"),
        (
            lambda report: report.update(
                verification_method="manual"
            ),
            "Playwright",
        ),
    ],
)
def test_invalid_verification_blocks_github(
    setup_pr_environment,
    monkeypatch,
    report_change,
    error_message,
):
    fake_github, report_path = setup_pr_environment

    report = create_valid_report()
    report_change(report)
    report_path.write_text(json.dumps(report), encoding="utf-8")

    monkeypatch.setattr(
        pull_request,
        "Github",
        lambda auth: pytest.fail("GitHub must not be contacted."),
    )

    with pytest.raises(RuntimeError, match=error_message):
        pull_request.create_pull_request(
            "mock-store/src/App.css",
            "Update CSS",
            "UI repair",
            "Test PR",
        )


def test_missing_report_blocks_github(setup_pr_environment, monkeypatch):
    fake_github, report_path = setup_pr_environment
    report_path.unlink()

    monkeypatch.setattr(
        pull_request,
        "Github",
        lambda auth: pytest.fail("GitHub must not be contacted."),
    )

    with pytest.raises(RuntimeError, match="missing"):
        pull_request.create_pull_request(
            "mock-store/src/App.css",
            "Update CSS",
            "UI repair",
            "Test PR",
        )


def test_no_source_changes_does_not_create_branch(
    setup_pr_environment,
):
    fake_github, _ = setup_pr_environment
    source_file = (
        pull_request.ROOT_DIR / "mock-store" / "src" / "App.css"
    )
    source_file.write_text("old content", encoding="utf-8")

    with pytest.raises(RuntimeError, match="No source changes"):
        pull_request.create_pull_request(
            "mock-store/src/App.css",
            "Update CSS",
            "UI repair",
            "Test PR",
        )

    assert fake_github.repo.branch_created is False
    assert fake_github.repo.pull_created is False
    assert fake_github.closed is True
