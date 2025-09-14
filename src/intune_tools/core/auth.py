"""
Authentication Manager for Intune Tools
========================================
Handles all authentication methods and credential management.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from azure.identity import (
    DeviceCodeCredential,
    InteractiveBrowserCredential,
    ClientSecretCredential,
    AuthenticationRecord,
    TokenCachePersistenceOptions
)
from azure.core.exceptions import ClientAuthenticationError
import keyring

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication for Microsoft Graph API"""

    PUBLIC_APP_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph PowerShell
    KEYRING_SERVICE = "IntuneMacOSTools"
    CACHE_DIR = Path.home() / ".intune-tools" / "auth"

    def __init__(self):
        self.credential = None
        self.auth_method = None
        self.tenant_id = None
        self.app_id = None
        self.is_authenticated = False
        self.user_info = None
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def authenticate_device_code(self, tenant_id: str = "common") -> bool:
        """
        Authenticate using device code flow
        """
        try:
            # Enable token cache
            cache_options = TokenCachePersistenceOptions(
                name="intune_tools_cache",
                enable_persistence=True
            )

            self.credential = DeviceCodeCredential(
                client_id=self.PUBLIC_APP_ID,
                tenant_id=tenant_id,
                cache_persistence_options=cache_options,
                prompt_callback=self._device_code_callback
            )

            self.auth_method = "device_code"
            self.tenant_id = tenant_id
            self.app_id = self.PUBLIC_APP_ID

            # Test authentication
            await self._validate_authentication()
            return True

        except Exception as e:
            logger.error(f"Device code authentication failed: {e}")
            raise

    async def authenticate_browser(self, tenant_id: str = "common") -> bool:
        """
        Authenticate using interactive browser flow
        """
        try:
            # Load cached authentication if available
            auth_record = self._load_auth_record()

            cache_options = TokenCachePersistenceOptions(
                name="intune_tools_cache",
                enable_persistence=True
            )

            self.credential = InteractiveBrowserCredential(
                client_id=self.PUBLIC_APP_ID,
                tenant_id=tenant_id,
                redirect_uri="http://localhost:8400",
                authentication_record=auth_record,
                cache_persistence_options=cache_options
            )

            self.auth_method = "browser"
            self.tenant_id = tenant_id
            self.app_id = self.PUBLIC_APP_ID

            # Test and save authentication
            await self._validate_authentication()

            # Save auth record for future use
            if hasattr(self.credential, 'authentication_record'):
                self._save_auth_record(self.credential.authentication_record)

            return True

        except Exception as e:
            logger.error(f"Browser authentication failed: {e}")

            # Fallback to device code if browser fails
            if "AADSTS50011" in str(e) or "redirect" in str(e).lower():
                logger.info("Browser auth failed, falling back to device code")
                return await self.authenticate_device_code(tenant_id)
            raise

    async def authenticate_custom(self, creds_path: str = "creds.json") -> bool:
        """
        Authenticate using custom app registration with client secret
        """
        try:
            # Load credentials
            creds = self._load_custom_credentials(creds_path)

            if not creds:
                raise ValueError(f"Could not load credentials from {creds_path}")

            # Try to get secret from keyring first
            client_secret = keyring.get_password(
                self.KEYRING_SERVICE,
                f"{creds['tenant_id']}:{creds['app_id']}"
            )

            if not client_secret:
                client_secret = creds.get('clientSecret')

                # Save to keyring for security
                if client_secret:
                    keyring.set_password(
                        self.KEYRING_SERVICE,
                        f"{creds['tenant_id']}:{creds['app_id']}",
                        client_secret
                    )

            self.credential = ClientSecretCredential(
                tenant_id=creds['tenant_id'],
                client_id=creds['app_id'],
                client_secret=client_secret
            )

            self.auth_method = "custom"
            self.tenant_id = creds['tenant_id']
            self.app_id = creds['app_id']

            # Validate authentication
            await self._validate_authentication()
            return True

        except Exception as e:
            logger.error(f"Custom app authentication failed: {e}")
            raise

    async def authenticate_certificate(self, cert_path: str, creds_path: str = "creds.json") -> bool:
        """
        Authenticate using certificate (more secure than client secret)
        """
        from azure.identity import CertificateCredential

        try:
            creds = self._load_custom_credentials(creds_path)

            if not creds:
                raise ValueError(f"Could not load credentials from {creds_path}")

            # Load certificate
            with open(cert_path, 'rb') as f:
                certificate_data = f.read()

            self.credential = CertificateCredential(
                tenant_id=creds['tenant_id'],
                client_id=creds['app_id'],
                certificate_data=certificate_data
            )

            self.auth_method = "certificate"
            self.tenant_id = creds['tenant_id']
            self.app_id = creds['app_id']

            await self._validate_authentication()
            return True

        except Exception as e:
            logger.error(f"Certificate authentication failed: {e}")
            raise

    async def refresh_token(self) -> bool:
        """
        Refresh the authentication token
        """
        try:
            if not self.credential:
                return False

            # Force token refresh by requesting a new token
            from azure.core.credentials import AccessToken
            token = await self._get_token_async()

            return token is not None

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False

    async def logout(self):
        """
        Logout and clear cached credentials
        """
        try:
            # Clear keyring entries
            if self.tenant_id and self.app_id:
                try:
                    keyring.delete_password(
                        self.KEYRING_SERVICE,
                        f"{self.tenant_id}:{self.app_id}"
                    )
                except:
                    pass

            # Clear auth record
            auth_record_path = self.CACHE_DIR / "auth_record.json"
            if auth_record_path.exists():
                auth_record_path.unlink()

            # Clear cached tokens
            cache_files = self.CACHE_DIR.glob("*.bin")
            for cache_file in cache_files:
                cache_file.unlink()

            self.credential = None
            self.is_authenticated = False
            self.user_info = None

            logger.info("Successfully logged out")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    def _device_code_callback(self, verification_uri: str, user_code: str, expires_on: datetime):
        """
        Callback for device code authentication
        """
        print("\n" + "=" * 60)
        print("DEVICE CODE AUTHENTICATION")
        print("=" * 60)
        print(f"\n1. Visit: {verification_uri}")
        print(f"2. Enter code: {user_code}")
        print(f"3. Expires at: {expires_on.strftime('%H:%M:%S')}")
        print("\nWaiting for authentication...")
        print("=" * 60 + "\n")

    def _load_custom_credentials(self, creds_path: str) -> Optional[Dict[str, str]]:
        """
        Load credentials from JSON file
        """
        creds_file = Path(creds_path)

        if not creds_file.exists():
            # Try in home directory
            alt_path = Path.home() / ".intune-tools" / "creds.json"
            if alt_path.exists():
                creds_file = alt_path
            else:
                return None

        try:
            with open(creds_file, 'r') as f:
                data = json.load(f)

            return {
                'app_id': data.get('appId', data.get('app_id')),
                'tenant_id': data.get('tenantId', data.get('tenant_id')),
                'clientSecret': data.get('clientSecret', data.get('client_secret'))
            }
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def _save_auth_record(self, auth_record: AuthenticationRecord):
        """
        Save authentication record for future use
        """
        try:
            auth_record_path = self.CACHE_DIR / "auth_record.json"
            with open(auth_record_path, 'w') as f:
                json.dump(auth_record.serialize(), f)
        except Exception as e:
            logger.debug(f"Could not save auth record: {e}")

    def _load_auth_record(self) -> Optional[AuthenticationRecord]:
        """
        Load saved authentication record
        """
        try:
            auth_record_path = self.CACHE_DIR / "auth_record.json"
            if auth_record_path.exists():
                with open(auth_record_path, 'r') as f:
                    data = json.load(f)
                return AuthenticationRecord.deserialize(data)
        except Exception as e:
            logger.debug(f"Could not load auth record: {e}")
        return None

    async def _validate_authentication(self):
        """
        Validate authentication by making a test API call
        """
        try:
            # Get a token to validate authentication
            token = await self._get_token_async()

            if token:
                self.is_authenticated = True
                logger.info(f"Authentication successful using {self.auth_method}")
            else:
                raise ClientAuthenticationError("Failed to obtain access token")

        except Exception as e:
            self.is_authenticated = False
            raise

    async def _get_token_async(self):
        """
        Get an access token asynchronously
        """
        try:
            # Run get_token in executor to avoid blocking
            loop = asyncio.get_event_loop()
            token = await loop.run_in_executor(
                None,
                self.credential.get_token,
                "https://graph.microsoft.com/.default"
            )
            return token
        except Exception as e:
            logger.error(f"Failed to get token: {e}")
            return None

    def get_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for API requests
        """
        if not self.credential:
            raise ValueError("Not authenticated")

        token = self.credential.get_token("https://graph.microsoft.com/.default")
        return {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }

    @property
    def is_custom_app(self) -> bool:
        """Check if using custom app registration"""
        return self.auth_method in ["custom", "certificate"]

    def get_required_permissions(self) -> list:
        """Get list of required Graph API permissions"""
        return [
            "DeviceManagementApps.ReadWrite.All",
            "DeviceManagementApps.Read.All",
            "DeviceManagementManagedDevices.ReadWrite.All",
            "DeviceManagementConfiguration.ReadWrite.All",
            "Group.Read.All",
            "User.Read.All",
            "Directory.Read.All",
            "AuditLog.Read.All"
        ]