import pytest
import os
import subprocess

import pgpm.lib.install


class TestInstallationManager:

    def test_install_uninstall_pgpm_to_from_db(self, installation_manager):
        assert installation_manager.install_pgpm_to_db(None) == 0
        assert installation_manager.uninstall_pgpm_from_db() == 0
