import json

def test_download_cs(crossection):
    # check if the dict has features in it
    assert("features" in crossection)