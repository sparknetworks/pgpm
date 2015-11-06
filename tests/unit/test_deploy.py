import pytest
import os
import subprocess

import pgpm.lib.install


class TestDeploymentManager:

    def test_deploy_schema_to_db(self, deployment_manager):
        assert deployment_manager.deploy_schema_to_db() == 0
