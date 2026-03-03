import os

from aiogoogle.auth.creds import (UserCreds, ClientCreds)
import aiofiles
import yaml

from src.aliases import Config


async def get_config(path: str) -> Config:
    """Load configuration variables from yaml file"""
    async with aiofiles.open(path, "r") as stream:
        content = await stream.read()
    return yaml.safe_load(content)


def get_user_creds(config: Config) -> UserCreds:
    """Get user credentials from config"""
    return UserCreds(
        access_token=config["user_creds"]["access_token"],
        refresh_token=config["user_creds"]["refresh_token"],
        expires_at=config["user_creds"]["expires_at"] or None,
    )


def get_client_creds(config: Config) -> ClientCreds:
    """Get client credentials from config"""
    return ClientCreds(
        client_id=config["client_creds"]["client_id"],
        client_secret=config["client_creds"]["client_secret"],
        scopes=config["client_creds"]["scopes"],
    )


def set_gemini_key(config: Config) -> None:
    """Load Gemini API key from config"""
    os.environ["GEMINI_API_KEY"] = config["gemini_key"]


def get_sheet_name(config: Config) -> str:
    """Get name of the Google spreadsheet with job data"""
    return config["sheet_name"]
