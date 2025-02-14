"""Test for security of water level retrieval scripts."""
import pytest

from nodeorc.water_level import check_script_security

def test_detect_risky_os_system_usage():
    script_content = "os.system('rm -rf /')"
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Use of risky function detected" in result["issues_found"][0]


def test_detect_risky_subprocess_usage():
    script_content = "subprocess.call(['ls', '-l'])"
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Use of risky function detected" in result["issues_found"][0]


def test_detect_eval_usage():
    script_content = "eval('os.system(\"rm -rf /\")')"
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Use of risky function detected" in result["issues_found"][0]


def test_detect_open_write_mode_usage():
    script_content = "open('test.txt', 'w')"
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Use of risky function detected" in result["issues_found"][0]


def test_detect_import_os_module():
    script_content = "import os"
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Use of risky function detected" in result["issues_found"][0]


def test_no_risky_usage():
    script_content = "print('Hello, World!')"
    result = check_script_security(script_content)
    assert result["is_safe"]
    assert not result["issues_found"]


def test_detect_risky_rm_rf_command():
    script_content = 'rm -rf /home/user'
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Risky shell command detected" in result["issues_found"][0]


def test_detect_wget_command():
    script_content = 'wget http://example.com/file'
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Risky shell command detected" in result["issues_found"][0]


def test_detect_sudo_command():
    script_content = "sudo apt-get install package"
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert "Risky shell command detected" in result["issues_found"][0]


def test_multiple_risks_in_script():
    script_content = """
    import os
    os.system('rm -rf /home/user')
    eval('print(\"Hello\")')
    """
    result = check_script_security(script_content)
    assert not result["is_safe"]
    assert len(result["issues_found"]) > 1

@pytest.mark.skip
def test_risks_real_script(script="g_red_api_request.sh"):
    with open(script, "r") as f:
        script_content = f.read()
    result = check_script_security(script_content)
    print(result)