import logging
import time
import webbrowser
import json
from typing import List

import requests
from requests.auth import HTTPBasicAuth


class InvalidTokenError(Exception):
    pass


class NotAuthenticatedError(Exception):
    pass


class InvalidClientError(Exception):
    pass


class RequestFailedError(Exception):
    pass


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str, scopes: List[str]):
        """
        A client wrapper for the Spotify Web API. Requires a client ID and client secret.
        :param client_id: The client ID of a valid Spotify application
        :param client_secret: The client secret of a valid Spotify application
        :param scopes: A list of required scopes
        """
        self.authenticated: bool = False
        self.access_token: str = None
        self.refresh_token: str = None
        self.scopes: List[str] = scopes
        self.client_id: str = client_id
        self.client_secret: str = client_secret

    def play(self):
        """
        Try to play Spotify.
        """
        try:
            self._send_common_request('api.spotify.com/v1/me/player/play', success_msg='Started playback', error_msg='Unable to play')
        except (TimeoutError, RequestFailedError, InvalidTokenError, NotAuthenticatedError):
            raise

    def pause(self):
        """
        Try to pause Spotify.
        """
        try:
            self._send_common_request('api.spotify.com/v1/me/player/pause', success_msg='Paused playback', error_msg='Unable to pause')
        except (TimeoutError, RequestFailedError, InvalidTokenError, NotAuthenticatedError):
            raise

    def set_volume(self, volume: int):
        """
        Try to set playback volume
        :param volume: Integer from 0 to 100, inclusive
        """
        try:
            self._send_common_request('api.spotify.com/v1/me/player/volume',
                                      params={'volume_percent': volume}, success_msg=f'Set volume to {volume}', error_msg='Unable to set volume')
        except (TimeoutError, RequestFailedError, InvalidTokenError, NotAuthenticatedError):
            raise

    def _send_common_request(self, base_url, success_msg: str, error_msg: str, params=None):
        """
        Wrapper to handle the majority of requests to the Spotify API
        :param base_url: The base URL of the request
        :param success_msg: The message to log on success
        :param error_msg: The message to log on error, as well as the text of the thrown error
        :param params: A dict of query params to send along with the request
        :raises NotAuthenticatedError: If the client is not currently authenticated
        See _parse_common_status for more exception information
        """
        if params is None:
            params = {}
        if self.authenticated:
            res = requests.put(f'https://{base_url}', params=params, headers={'Authorization': f'Bearer {self.access_token}'})
            if res.status_code == 202:
                for tries in range(5):
                    logging.warning('Spotify: device temporarily unavailable. Trying again in 5 seconds')
                    time.sleep(5)
                    res = requests.put(f'https://{base_url}', headers={'Authorization': f'Bearer {self.access_token}'})
                    if res.status_code == 204:
                        break
                    if tries == 4:
                        raise TimeoutError

            try:
                self._parse_common_status(res, success_msg=success_msg, error_msg=error_msg)
            except (RequestFailedError, InvalidTokenError):
                raise
        else:
            raise NotAuthenticatedError

    def _parse_common_status(self, res: requests.Response, success_msg: str, error_msg: str):
        """
        Parse the response sent from the majority of requests to the Spotify API
        :param res: The response to parse
        :param success_msg: The message to log on success
        :param error_msg: The message to log on error, as well as the text of the thrown error
        :raises TimeoutError: If the request timed out
                RequestFailedError: If the request could not be completed
                InvalidTokenError: If the client appeared to be authenticated but the access_token was invalid
        """
        if res.status_code == 204:
            logging.info(f'Spotify: {success_msg}')
        elif res.status_code == 404:
            logging.error('Spotify: playback device not found')
            logging.debug(res.text)
            raise RequestFailedError('Playback device not found')
        elif res.status_code == 403:
            logging.error(f'Spotify: {error_msg}')
            logging.debug(res.text)
            raise RequestFailedError(error_msg)
        elif res.status_code == 401:
            self.authenticated = False
            logging.error('Spotify: access_token is invalid.')
            logging.debug(res.text)
            raise InvalidTokenError('access_token is invalid')
        else:
            logging.error('Spotify: request failed')
            logging.debug(res.text)
            raise RequestFailedError('Unhandled response code')

    def authenticate(self):
        """
        Try to authenticate with a refresh token, if found. If not, the user will be redirected to the browser for the OAuth2 process
        :raises KeyError: If the response from Spotify does not contain 'scope', 'access_token', and 'refresh_token'
        :raises AssertionError: If the response from Spotify is not 200 or does not match the requested scopes
        :raises OSError: If the a returned refresh_token could not be written to the refresh.token file
        :raises IOError: If the a returned refresh_token could not be written to the refresh.token file
        """
        try:
            with open('refresh.token', 'r') as token_file:
                refresh_token = token_file.readline().rstrip()

            self.refresh_token = refresh_token
            self.refresh()
        except (OSError, IOError, FileNotFoundError, InvalidTokenError) as e:
            logging.warning('Unable to authenticate with "refresh.token" file')
            logging.debug(e)

            response_type = 'code'
            redirect_uri = 'https://localhost/'

            base_url = 'accounts.spotify.com/authorize'
            auth_url = (f'https://{base_url}/'
                        f'?client_id={self.client_id}'
                        f'&response_type={response_type}'
                        f'&redirect_uri={redirect_uri}'
                        f'&scope={" ".join(self.scopes)}'
                        )

            print('A browser window will be opened so that you can authorize this app')
            print('After you press enter, authenticate with Spotify and paste the "code" parameter at the next prompt')
            input('<press Enter to continue>')

            logging.info(f'opening {auth_url} in browser')
            webbrowser.open(auth_url, new=2, autoraise=True)

            auth_code = input('Please paste the "code" parameter from the URL here: ')

            access_url = 'accounts.spotify.com/api/token'
            grant_type = 'authorization_code'

            data = {
                'grant_type': grant_type,
                'code': auth_code,
                'redirect_uri': redirect_uri,
                # 'client_id': self.client_id,
                # 'client_secret': self.client_secret
            }

            res = requests.post(f'https://{access_url}', data=data, auth=HTTPBasicAuth(self.client_id, self.client_secret))
            try:
                assert res.status_code == 200
                res_data = json.loads(res.text)
                assert res_data['scope'].split(' ') == self.scopes
                access_token = res_data['access_token']
                refresh_token = res_data['refresh_token']

                self.access_token = access_token
                self.refresh_token = refresh_token
                self.authenticated = True
            except (KeyError, AssertionError) as e:
                logging.critical('Authentication failed.')
                logging.debug(f'{res.status_code}: {res.text}')
                logging.debug(e)
                raise e
            logging.info('Spotify: Authentication succeeded')

            try:
                with open('refresh.token', 'w') as token_file:
                    print(self.refresh_token, file=token_file)
            except (OSError, IOError) as e:
                logging.warning('Unable to write to file "refresh.token". Refresh token will not persist')
                logging.debug(e)
                raise e

    def refresh(self):
        """
        Attempt to refresh the Spotify access token using the refresh token.
        Will fail
        :raises InvalidClientError: If client_id, client_secret, or refresh_token are not set
        :raises InvalidTokenError: If the refresh_token is invalid (Most likely was revoked by the user)
        """
        if not(self.client_id and self.client_secret and self.refresh_token):
            logging.warning('Cannot refresh if client_id, client_secret, or refresh_token are not set')
            logging.debug(f'client_id: {self.client_id}, client_secret: {self.client_secret}, refresh_token: {self.refresh_token}')
            raise InvalidClientError

        base_url = 'accounts.spotify.com/api/token'

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }

        res = requests.post(f'https://{base_url}', data=data, auth=HTTPBasicAuth(self.client_id, self.client_secret))
        try:
            assert res.status_code == 200
            res_data = json.loads(res.text)
            assert res_data['scope'].split(' ') == self.scopes
            access_token = res_data['access_token']
            self.access_token = access_token
            self.authenticated = True
        except (KeyError, AssertionError) as e:
            if res.status_code == 400:
                logging.info('Spotify: Refresh token is invalid. Please delete file "refresh.token"')
            logging.debug(f'{res.status_code}: {res.text}')
            logging.debug(e)
            raise InvalidTokenError
        logging.info('Spotify: Authentication with refresh token succeeded')
