import pytest
import os
import subprocess

import pgpm.lib.install


class TestInstallationManager:

    def test_install_pgpm_to_db(self, installation_manager):
        assert installation_manager.install_pgpm_to_db(None) == 0
