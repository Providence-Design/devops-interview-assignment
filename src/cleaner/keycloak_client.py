"""Keycloak Admin API client.

Suggested shape:
    - get_token()          - fetch an access token via client_credentials
    - list_users()         - paginate through the realm's users
    - delete_user(user_id) - delete (or disable, if you prefer soft delete)

You can use `python-keycloak`, `requests`, `httpx`, or roll your own.
No requirement — pick whatever fits your approach.
"""

from __future__ import annotations
import httpx

class KeycloakClient:
    def __init__(self, base_url: str, realm: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self._token : str | None = None
        self._client = httpx.Client(timeout=10.0)

    def get_token(self) -> str:
        if self._token is not None:
            return self._token
        
        url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
        resp = self._client.post(
           url,
           data={
              "grant_type": "client_credentials",
              "client_id": self.client_id,
              "client_secret": self.client_secret,

           },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token
      

    def list_users(self):
        first = 0
        page_size = 100
        base = f"{self.base_url}/admin/realms/{self.realm}/users"
        headers = {"Authorization" : f"Bearer {self.get_token()}"}

        while True:
           resp = self._client.get(
             base,
             headers=headers,
             params={"first" : first, "max": page_size, "briefRepresentation": "false"},    
           )
            
           resp.raise_for_status()
           page = resp.json()

           if not page:
               return
           for user in page:
              yield  user

           if len(page) < page_size:
             return
           first += page_size
                  

    def delete_user(self, user_id: str) -> None:
        # TODO: implement user deletion (or soft-delete via disable — your call)
        raise NotImplementedError
