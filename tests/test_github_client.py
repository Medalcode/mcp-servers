import pytest
from unittest.mock import patch, AsyncMock


@pytest.fixture(autouse=True)
async def _reset_client():
    from gh_mcp import client
    client._shared_client = None


@pytest.fixture(autouse=True)
def _mock_token():
    with patch("gh_mcp.client._check_token", return_value=True):
        yield


class TestGithubClient:
    @patch("gh_mcp.client._get")
    async def test_get_repo(self, mock_get):
        mock_get.return_value = {
            "full_name": "owner/repo",
            "description": "A test repo",
            "stargazers_count": 42,
            "forks_count": 10,
            "open_issues_count": 3,
            "language": "Python",
            "default_branch": "main",
            "visibility": "public",
            "size": 100,
            "topics": ["python", "test"],
            "html_url": "https://github.com/owner/repo",
        }
        from gh_mcp.client import get_repo
        result = await get_repo("owner/repo")
        assert "owner/repo" in result
        assert "42" in result
        assert "Python" in result

    async def test_get_repo_no_token(self):
        with patch("gh_mcp.client._check_token", return_value=False):
            from gh_mcp.client import get_repo
            result = await get_repo("owner/repo")
            assert "GITHUB_TOKEN not configured" in result

    @patch("gh_mcp.client._get")
    async def test_search_repositories(self, mock_get):
        mock_get.return_value = {
            "items": [
                {"full_name": "owner/a", "stargazers_count": 10, "description": "Repo A"},
                {"full_name": "owner/b", "stargazers_count": 5, "description": "Repo B"},
            ]
        }
        from gh_mcp.client import search_repositories
        result = await search_repositories("test query")
        assert "owner/a" in result
        assert "Repo A" in result

    @patch("gh_mcp.client._get")
    async def test_get_file_content(self, mock_get):
        import base64
        content = base64.b64encode(b"print('hello')").decode()
        mock_get.return_value = {"content": content, "encoding": "base64"}
        from gh_mcp.client import get_file_content
        result = await get_file_content("owner/repo", "main.py")
        assert "print('hello')" in result

    @patch("gh_mcp.client._get")
    async def test_get_file_content_directory(self, mock_get):
        mock_get.return_value = [{"name": "a.py"}, {"name": "b.py"}]
        from gh_mcp.client import get_file_content
        result = await get_file_content("owner/repo", "src")
        assert "a.py" in result

    @patch("gh_mcp.client._get")
    async def test_list_issues(self, mock_get):
        mock_get.return_value = [
            {"number": 1, "title": "Bug fix", "state": "open", "user": {"login": "user1"}, "labels": []},
        ]
        from gh_mcp.client import list_issues
        result = await list_issues("owner/repo")
        assert "Bug fix" in result

    @patch("gh_mcp.client._get")
    async def test_list_issues_empty(self, mock_get):
        mock_get.return_value = []
        from gh_mcp.client import list_issues
        result = await list_issues("owner/repo")
        assert "No open issues found" in result

    @patch("gh_mcp.client._post")
    async def test_create_issue(self, mock_post):
        mock_post.return_value = {"number": 42, "html_url": "https://github.com/owner/repo/issues/42"}
        from gh_mcp.client import create_issue
        result = await create_issue("owner/repo", "Test issue", "body text")
        assert "Created issue #42" in result

    @patch("gh_mcp.client._patch")
    async def test_close_issue(self, mock_patch):
        mock_patch.return_value = {"number": 42, "title": "Test issue"}
        from gh_mcp.client import close_issue
        result = await close_issue("owner/repo", 42)
        assert "Closed issue" in result

    @patch("gh_mcp.client._get")
    async def test_get_issue(self, mock_get):
        mock_get.return_value = {
            "number": 1, "title": "Bug", "state": "open",
            "user": {"login": "user1"},
            "labels": [{"name": "bug"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/1",
            "body": "Description here",
        }
        from gh_mcp.client import get_issue
        result = await get_issue("owner/repo", 1)
        assert "#1 Bug" in result
        assert "Description" in result

    @patch("gh_mcp.client._get")
    async def test_list_prs(self, mock_get):
        mock_get.return_value = [
            {"number": 1, "title": "PR 1", "state": "open", "user": {"login": "user1"},
             "base": {"ref": "main"}, "head": {"ref": "feature"}, "draft": False},
        ]
        from gh_mcp.client import list_prs
        result = await list_prs("owner/repo")
        assert "PR 1" in result

    @patch("gh_mcp.client._get")
    async def test_list_branches(self, mock_get):
        mock_get.return_value = [
            {"name": "main", "protected": True},
            {"name": "dev", "protected": False},
        ]
        from gh_mcp.client import list_branches
        result = await list_branches("owner/repo")
        assert "main" in result

    @patch("gh_mcp.client._get")
    async def test_list_commits(self, mock_get):
        mock_get.return_value = [
            {"sha": "abc123def", "commit": {"message": "Fix bug\nDetails...", "author": {"name": "Alice", "date": "2024-01-01T00:00:00Z"}}},
        ]
        from gh_mcp.client import list_commits
        result = await list_commits("owner/repo")
        assert "abc123d" in result
        assert "Alice" in result

    @patch("gh_mcp.client._put")
    async def test_merge_pr(self, mock_put):
        mock_put.return_value = {"merged": True, "message": "Pull request merged"}
        from gh_mcp.client import merge_pr
        result = await merge_pr("owner/repo", 1)
        assert "Merged" in result

    @patch("gh_mcp.client._get")
    async def test_list_workflows(self, mock_get):
        mock_get.return_value = {
            "workflows": [
                {"name": "CI", "path": ".github/workflows/ci.yml", "state": "active"},
                {"name": "Deploy", "path": ".github/workflows/deploy.yml", "state": "disabled"},
            ]
        }
        from gh_mcp.client import list_workflows
        result = await list_workflows("owner/repo")
        assert "CI" in result

    @patch("gh_mcp.client._post")
    @patch("gh_mcp.client._get")
    async def test_trigger_workflow(self, mock_get, mock_post):
        mock_get.return_value = {
            "workflows": [{"name": "CI", "path": ".github/workflows/ci.yml", "id": 123, "state": "active"}]
        }
        mock_post.return_value = {}
        from gh_mcp.client import trigger_workflow
        result = await trigger_workflow("owner/repo", "CI")
        assert "Triggered" in result
