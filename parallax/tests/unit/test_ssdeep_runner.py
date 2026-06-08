from unittest.mock import patch
from parallax.analysis.ingestion.ssdeep_runner import run_ssdeep


@patch("parallax.analysis.ingestion.ssdeep_runner.subprocess.run")
def test_run_ssdeep_success(mock_subprocess_run):
    """Test successful ssdeep execution."""
    mock_subprocess_run.return_value.returncode = 0
    # ssdeep output has a header line and then the hash line
    mock_subprocess_run.return_value.stdout = 'ssdeep,1.1--blocksize:hash:hash,filename\n12288:xyz123:abc456,"test.apk"'
    
    result = run_ssdeep("test.apk")
    assert "hash" in result
    assert result["hash"] == "12288:xyz123:abc456"


@patch("parallax.analysis.ingestion.ssdeep_runner.subprocess.run")
def test_run_ssdeep_failure(mock_subprocess_run):
    """Test ssdeep execution failure."""
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stdout = ""
    mock_subprocess_run.return_value.stderr = "Error"
    
    result = run_ssdeep("test.apk")
    assert "error" in result
    assert result["error"] == "ssdeep execution failed"


@patch("parallax.analysis.ingestion.ssdeep_runner.subprocess.run")
def test_run_ssdeep_not_found(mock_subprocess_run):
    """Test ssdeep not installed."""
    mock_subprocess_run.side_effect = FileNotFoundError()
    
    result = run_ssdeep("test.apk")
    assert "error" in result
    assert result["error"] == "ssdeep not installed"
