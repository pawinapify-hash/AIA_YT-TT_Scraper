from status_control import is_run_active


def test_stop_status_is_not_active():
    assert is_run_active("🔴 Stop") is False


def test_start_status_is_active():
    assert is_run_active("🟢 Start") is True


def test_plain_start_status_is_active():
    assert is_run_active("Start") is True
