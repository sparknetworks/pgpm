import pytest
import os
import subprocess

import pgpm.lib.install


class TestDeploymentManager:

    def test_deploy_schema_to_db(self, installation_manager, deployment_manager):
        assert installation_manager.install_pgpm_to_db(None) == 0
        assert deployment_manager.deploy_schema_to_db() == 0
        assert installation_manager.uninstall_pgpm_from_db() == 0
