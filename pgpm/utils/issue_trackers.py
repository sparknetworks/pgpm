import json
import logging
import requests
import requests.auth
import os


class Jira:
    """
    Manages connection to JIRA
    """

    def __init__(self, base_url="localhost", logger=None):
        """
        populates properties with config data
        """
        self._logger = logger or logging.getLogger(__name__)
        self.base_url = base_url

    def call_jira_rest(self, url, user, password, method="GET", data=None):
        """
        Make JIRA REST call
        :param data: data for rest call
        :param method: type of call: GET or POST for now
        :param url: url to call
        :param user: user for authentication
        :param password: password for authentication
        :return:
        """
        headers = {'content-type': 'application/json'}

        self._logger.debug('Connecting to Jira to call the following REST method {0}'.format(url))
        if method == "GET":
            response = requests.get(self.base_url + url, auth=requests.auth.HTTPBasicAuth(user, password))
        elif method == "POST":
            response = requests.post(self.base_url + url, data=json.dumps(data),
                                     auth=requests.auth.HTTPBasicAuth(user, password), headers=headers)
        else:
            raise ValueError('method argument supports GET or POST values only')
        self._logger.debug('REST call successfully finalised')
        return response.json()