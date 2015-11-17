import pytest
import os
import subprocess

import pgpm.lib.install


def get_pgpm_path():
    """
    returns path to directory that contains pgpm module
    :return:
    """
    import pgpm
    import inspect

    main_path = os.path.dirname(os.path.dirname(inspect.getfile(pgpm)))
    return main_path


TEST_SCHEMA_LOW_0_5_0_PATH = get_pgpm_path() + "/tests/fixtures/pgpm_packages/test_schema_low_0_5_0"
TEST_SCHEMA_TOP_0_1_0_PATH = get_pgpm_path() + "/tests/fixtures/pgpm_packages/test_schema_top_0_1_0"
TEST_SCHEMA_TOP_0_2_0_PATH = get_pgpm_path() + "/tests/fixtures/pgpm_packages/test_schema_top_0_2_0"
TEST_CONFIG_FILE_NAME = "config.json"


class TestDeploymentManager:

    def test_deploy_schema_to_db(self, installation_manager, deployment_manager):
        assert installation_manager.install_pgpm_to_db(None) == 0
        assert deployment_manager.deploy_schema_to_db(
            config_path=os.path.join(TEST_SCHEMA_LOW_0_5_0_PATH, TEST_CONFIG_FILE_NAME),
            source_code_path=TEST_SCHEMA_LOW_0_5_0_PATH) == 0
        assert deployment_manager.deploy_schema_to_db(
            config_path=os.path.join(TEST_SCHEMA_TOP_0_1_0_PATH, TEST_CONFIG_FILE_NAME),
            source_code_path=TEST_SCHEMA_TOP_0_1_0_PATH) == 0
        assert deployment_manager.deploy_schema_to_db(
            config_path=os.path.join(TEST_SCHEMA_TOP_0_2_0_PATH, TEST_CONFIG_FILE_NAME),
            source_code_path=TEST_SCHEMA_TOP_0_2_0_PATH) == 0
        assert installation_manager.uninstall_pgpm_from_db() == 0
