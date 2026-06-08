from unittest.mock import patch

from parallax.analysis.ingestion.apkid_runner import run_apkid


@patch("parallax.analysis.ingestion.apkid_runner.subprocess.run")
def test_run_apkid_success(mock_subprocess_run):
    """Test successful APKiD execution."""
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = (
        '{"files": [{"filename": "test.apk", "matches": {"compiler": ["d8"]}}]}'
    )

    result = run_apkid("test.apk")
    assert "matches" in result
    assert result["matches"]["compiler"] == ["d8"]


@patch("parallax.analysis.ingestion.apkid_runner.subprocess.run")
def test_run_apkid_failure(mock_subprocess_run):
    """Test APKiD execution failure."""
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stdout = ""
    mock_subprocess_run.return_value.stderr = "Error"

    result = run_apkid("test.apk")
    assert "error" in result
    assert result["error"] == "APKiD execution failed"


@patch("parallax.analysis.ingestion.apkid_runner.subprocess.run")
def test_run_apkid_not_found(mock_subprocess_run):
    """Test APKiD not installed."""
    mock_subprocess_run.side_effect = FileNotFoundError()

    result = run_apkid("test.apk")
    assert "error" in result
    assert result["error"] == "apkid not installed"
