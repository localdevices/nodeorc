import os
from nodeorc import disk_mng
import logging

import os
import shutil
import tempfile

import numpy as np
import pytest
from nodeorc.disk_mng import scan_folder


def create_test_structure(base_dir, structure):
    """
    Helper function to create a test folder structure.
    `structure` is a dict with nested directory and file names as keys and values.
    """
    for folder, content in structure.items():
        folder_path = os.path.join(base_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        if isinstance(content, list):
            for item in content:
                # Create a file
                open(os.path.join(folder_path, item), 'w').close()
        elif isinstance(content, dict):
            # Subdirectory
            create_test_structure(folder_path, content)


@pytest.fixture
def sample_directory():
    # Create a temporary directory and return its path
    with tempfile.TemporaryDirectory() as temp_dir:
        structure = {
            "folder1": ["file1.txt", "file2.log", "file3.txt"],
            "folder2": ["file4.log"],
            "folder3": {
                "subfolder1": ["file5.txt"],
                "subfolder2": []  # empty folder
            },
            "empty_folder": []  # another empty folder
        }
        create_test_structure(temp_dir, structure)
        yield temp_dir


def test_scan_folder_with_txt_suffix(sample_directory):
    suffix = ".txt"
    result = scan_folder(sample_directory, suffix=suffix)
    expected_files = [
        os.path.join(sample_directory, "folder1", "file1.txt"),
        os.path.join(sample_directory, "folder1", "file3.txt"),
        os.path.join(sample_directory, "folder3", "subfolder1", "file5.txt"),
    ]
    assert sorted(result) == sorted(expected_files)


def test_scan_folder_with_txt_suffix_bytes(sample_directory):
    suffix = ".txt"
    sample_directory_b = sample_directory.encode()
    result = scan_folder(sample_directory_b, suffix=suffix)
    expected_files = [
        os.path.join(sample_directory, "folder1", "file1.txt"),
        os.path.join(sample_directory, "folder1", "file3.txt"),
        os.path.join(sample_directory, "folder3", "subfolder1", "file5.txt"),
    ]
    assert sorted(result) == sorted(expected_files)


def test_scan_folder_with_log_suffix(sample_directory):
    suffix = ".log"
    result = scan_folder(sample_directory, suffix=suffix)
    expected_files = [
        os.path.join(sample_directory, "folder1", "file2.log"),
        os.path.join(sample_directory, "folder2", "file4.log"),
    ]
    assert sorted(result) == sorted(expected_files)


def test_scan_folder_without_suffix(sample_directory):
    result = scan_folder(sample_directory)
    expected_files = [
        os.path.join(sample_directory, "folder1", "file1.txt"),
        os.path.join(sample_directory, "folder1", "file2.log"),
        os.path.join(sample_directory, "folder1", "file3.txt"),
        os.path.join(sample_directory, "folder2", "file4.log"),
        os.path.join(sample_directory, "folder3", "subfolder1", "file5.txt"),
    ]
    assert sorted(result) == sorted(expected_files)


def test_scan_folder_removes_empty_dirs(sample_directory):
    scan_folder(sample_directory, clean_empty_dirs=True)
    assert not os.path.exists(os.path.join(sample_directory, "folder3", "subfolder2"))
    assert not os.path.exists(os.path.join(sample_directory, "empty_folder"))


def test_scan_folder_keeps_empty_dirs(sample_directory):
    scan_folder(sample_directory, clean_empty_dirs=False)
    assert os.path.exists(os.path.join(sample_directory, "folder3", "subfolder2"))
    assert os.path.exists(os.path.join(sample_directory, "empty_folder"))


def test_scan_folder_with_empty_input():
    result = scan_folder([], clean_empty_dirs=True)
    assert result == []


def test_scan_folder_with_non_existent_directory():
    non_existent_dir = "/non/existent/directory"
    result = scan_folder(non_existent_dir, clean_empty_dirs=True)
    assert result == []

