"""Configuration loading.

Reads from environment variables. See .env.example for the expected shape.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    keycloak_url: str
    realm: str
    client_id: str
    client_secret: str
    inactivity_days: int
    dry_run: bool
    exclusions: list[str]

    @classmethod
    def from_env(cls) -> "Config":
        keycloak_url = os.environ["KEYCLOAK_URL"]
        realm = os.environ["KEYCLOAK_REALM"]
        client_id = os.environ["KEYCLOAK_CLIENT_ID"]
        client_secret = os.environ["KEYCLOAK_CLIENT_SECRET"]

        inactivity_days = int(os.environ.get("INACTIVITY_DAYS", "120"))
        dry_run_raw =  os.environ.get("DRY_RUN", "true")
        dry_run = dry_run_raw.strip().lower() in ("1", "true", "yes")

        exclusions_raw = os.environ.get("EXCLUSIONS", "")
        exclusions = [name.strip() for name in  exclusions_raw.split(",") if name.strip()]
       
        return cls(
           keycloak_url=keycloak_url,
           realm=realm,
           client_id=client_id,
           client_secret=client_secret,
           inactivity_days=inactivity_days,
           dry_run=dry_run,
           exclusions=exclusions,
           
       )
        