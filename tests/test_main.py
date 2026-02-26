from deltaforcescript.runtime_utils import extract_and_merge_digits


def test_extract_and_merge_digits():
    assert extract_and_merge_digits("12分 03秒") == "1203"
