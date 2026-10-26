import os, tempfile
os.environ["WORKDIR"] = tempfile.mkdtemp()

import pytest
from app import agent


def test_path_aman_tolak_keluar_folder():
    with pytest.raises(ValueError):
        agent.path_aman("../rahasia.txt")
    with pytest.raises(ValueError):
        agent.path_aman(agent.WORKDIR + "-lain/x")


def test_tulis_baca_file():
    agent.write_file("sub/a.txt", "halo")
    assert agent.read_file("sub/a.txt") == "halo"
    assert "sub/a.txt" in agent.list_files()


def test_session_id_disanitasi():
    assert os.path.dirname(agent.file_session("../../etc/passwd")) == agent.SESSION_DIR


def test_shell_mati_default():
    assert "dinonaktifkan" in agent.run_shell("echo hi")
