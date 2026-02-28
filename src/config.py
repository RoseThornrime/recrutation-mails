import os

from aiogoogle.auth.creds import (UserCreds, ClientCreds)
import yaml


def get_config(path):
    with open(path, "r") as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    return config

def get_user_creds(config):
    return UserCreds(
        access_token=config["user_creds"]["access_token"],
        refresh_token=config["user_creds"]["refresh_token"],
        expires_at=config["user_creds"]["expires_at"] or None,
    )


def get_client_creds(config):
    return ClientCreds(
        client_id=config["client_creds"]["client_id"],
        client_secret=config["client_creds"]["client_secret"],
        scopes=config["client_creds"]["scopes"],
    )


def set_gemini_key(config):
    os.environ["GEMINI_API_KEY"] = config["gemini_key"]


def get_sheet_name(config):
    return config["sheet_name"]
