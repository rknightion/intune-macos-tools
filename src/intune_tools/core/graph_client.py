"""
Microsoft Graph API Client
===========================
Handles all Graph API interactions for Intune management.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from msgraph import GraphServiceClient
from azure.identity import TokenCredential
from kiota_abstractions.api_error import APIError
import aiohttp

logger = logging.getLogger(__name__)


class GraphClient:
    """Wrapper for Microsoft Graph API operations"""

    def __init__(self, credential: TokenCredential):
        self.credential = credential
        self.client = GraphServiceClient(
            credentials=credential,
            scopes=["https://graph.microsoft.com/.default"]
        )
        self._session = None

    async def __aenter__(self):
        """Async context manager entry"""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()

    # =========================================================================
    # User and Group Operations
    # =========================================================================

    async def get_current_user(self) -> Dict[str, Any]:
        """Get current authenticated user information"""
        try:
            user = await self.client.me.get()
            return {
                'id': user.id,
                'displayName': user.display_name,
                'userPrincipalName': user.user_principal_name,
                'mail': user.mail,
                'jobTitle': user.job_title
            }
        except Exception as e:
            logger.error(f"Failed to get current user: {e}")
            raise

    async def get_all_groups(self) -> List[Dict[str, Any]]:
        """Get all groups in the tenant"""
        try:
            groups = []
            response = await self.client.groups.get()

            while response:
                if response.value:
                    for group in response.value:
                        groups.append({
                            'id': group.id,
                            'displayName': group.display_name,
                            'description': group.description,
                            'mail': group.mail,
                            'securityEnabled': group.security_enabled,
                            'mailEnabled': group.mail_enabled,
                            'groupTypes': group.group_types,
                            'memberCount': await self._get_group_member_count(group.id)
                        })

                # Check for next page
                if hasattr(response, 'odata_next_link') and response.odata_next_link:
                    response = await self.client.groups.with_url(response.odata_next_link).get()
                else:
                    break

            return groups

        except Exception as e:
            logger.error(f"Failed to get groups: {e}")
            raise

    async def _get_group_member_count(self, group_id: str) -> int:
        """Get member count for a group"""
        try:
            members = await self.client.groups.by_group_id(group_id).members.get()
            return len(members.value) if members and members.value else 0
        except:
            return 0

    async def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """Get members of a specific group"""
        try:
            members = []
            response = await self.client.groups.by_group_id(group_id).members.get()

            if response and response.value:
                for member in response.value:
                    members.append({
                        'id': member.id,
                        'displayName': getattr(member, 'display_name', 'Unknown'),
                        'type': member.odata_type
                    })

            return members

        except Exception as e:
            logger.error(f"Failed to get group members: {e}")
            raise

    # =========================================================================
    # Application Operations
    # =========================================================================

    async def get_all_apps(self) -> List[Dict[str, Any]]:
        """Get all applications from Intune"""
        try:
            apps = []
            response = await self.client.device_app_management.mobile_apps.get()

            while response:
                if response.value:
                    for app in response.value:
                        apps.append(self._parse_app(app))

                # Check for next page
                if hasattr(response, 'odata_next_link') and response.odata_next_link:
                    response = await self.client.device_app_management.mobile_apps.with_url(
                        response.odata_next_link
                    ).get()
                else:
                    break

            return apps

        except Exception as e:
            logger.error(f"Failed to get apps: {e}")
            raise

    async def get_macos_apps(self) -> List[Dict[str, Any]]:
        """Get only macOS applications"""
        all_apps = await self.get_all_apps()

        macos_types = [
            "macOSLobApp", "macOSOfficeSuiteApp", "macOSMicrosoftEdgeApp",
            "macOSMicrosoftDefenderApp", "macOSWebClip", "macOSVppApp",
            "macOSPkgApp", "macOSDmgApp", "macOSMdmApp", "macOSCustomApp"
        ]

        return [
            app for app in all_apps
            if any(mt in app.get('type', '') for mt in macos_types)
        ]

    async def get_app_details(self, app_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific app"""
        try:
            app = await self.client.device_app_management.mobile_apps.by_mobile_app_id(app_id).get()
            return self._parse_app(app)
        except Exception as e:
            logger.error(f"Failed to get app details: {e}")
            raise

    async def get_app_assignments(self, app_id: str) -> List[Dict[str, Any]]:
        """Get assignments for a specific app"""
        try:
            assignments = []
            response = await self.client.device_app_management.mobile_apps.by_mobile_app_id(
                app_id
            ).assignments.get()

            if response and response.value:
                for assignment in response.value:
                    assignments.append({
                        'id': assignment.id,
                        'intent': str(assignment.intent),
                        'target': self._parse_assignment_target(assignment.target),
                        'settings': self._parse_assignment_settings(assignment.settings)
                    })

            return assignments

        except Exception as e:
            logger.error(f"Failed to get app assignments: {e}")
            raise

    def _parse_app(self, app) -> Dict[str, Any]:
        """Parse app object to dictionary"""
        return {
            'id': app.id,
            'displayName': app.display_name,
            'description': app.description,
            'publisher': app.publisher,
            'type': app.odata_type.replace("#microsoft.graph.", "") if app.odata_type else "Unknown",
            'createdDateTime': app.created_date_time,
            'lastModifiedDateTime': app.last_modified_date_time,
            'version': getattr(app, 'version', 'N/A'),
            'size': getattr(app, 'size', 0),
            'isFeatured': getattr(app, 'is_featured', False),
            'privacyInformationUrl': getattr(app, 'privacy_information_url', None),
            'informationUrl': getattr(app, 'information_url', None),
            'notes': getattr(app, 'notes', None)
        }

    def _parse_assignment_target(self, target) -> Dict[str, Any]:
        """Parse assignment target"""
        if not target:
            return {'type': 'unknown'}

        target_type = target.odata_type if hasattr(target, 'odata_type') else 'unknown'

        result = {'type': target_type}

        if 'group' in target_type.lower() and hasattr(target, 'group_id'):
            result['groupId'] = target.group_id

        return result

    def _parse_assignment_settings(self, settings) -> Dict[str, Any]:
        """Parse assignment settings"""
        if not settings:
            return {}

        return {
            'notifications': getattr(settings, 'notifications', 'showAll'),
            'restartRequired': getattr(settings, 'restart_required', False),
            'installTimeSettings': getattr(settings, 'install_time_settings', None)
        }

    # =========================================================================
    # Device Operations
    # =========================================================================

    async def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all managed devices"""
        try:
            devices = []
            response = await self.client.device_management.managed_devices.get()

            while response:
                if response.value:
                    for device in response.value:
                        devices.append(self._parse_device(device))

                # Check for next page
                if hasattr(response, 'odata_next_link') and response.odata_next_link:
                    response = await self.client.device_management.managed_devices.with_url(
                        response.odata_next_link
                    ).get()
                else:
                    break

            return devices

        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            raise

    async def get_macos_devices(self) -> List[Dict[str, Any]]:
        """Get only macOS devices"""
        all_devices = await self.get_all_devices()
        return [d for d in all_devices if d.get('operatingSystem', '').lower() == 'macos']

    def _parse_device(self, device) -> Dict[str, Any]:
        """Parse device object to dictionary"""
        return {
            'id': device.id,
            'deviceName': device.device_name,
            'operatingSystem': device.operating_system,
            'osVersion': device.os_version,
            'userDisplayName': device.user_display_name,
            'userPrincipalName': device.user_principal_name,
            'enrolledDateTime': device.enrolled_date_time,
            'lastSyncDateTime': device.last_sync_date_time,
            'complianceState': device.compliance_state,
            'model': device.model,
            'manufacturer': device.manufacturer,
            'serialNumber': device.serial_number,
            'managementState': device.management_state,
            'isEncrypted': device.is_encrypted,
            'totalStorageSpace': device.total_storage_space_in_bytes,
            'freeStorageSpace': device.free_storage_space_in_bytes
        }

    # =========================================================================
    # Policy Operations
    # =========================================================================

    async def get_compliance_policies(self) -> List[Dict[str, Any]]:
        """Get all compliance policies"""
        try:
            policies = []
            response = await self.client.device_management.device_compliance_policies.get()

            if response and response.value:
                for policy in response.value:
                    policies.append({
                        'id': policy.id,
                        'displayName': policy.display_name,
                        'description': policy.description,
                        'createdDateTime': policy.created_date_time,
                        'lastModifiedDateTime': policy.last_modified_date_time,
                        'version': policy.version
                    })

            return policies

        except Exception as e:
            logger.error(f"Failed to get compliance policies: {e}")
            raise

    async def get_configuration_profiles(self) -> List[Dict[str, Any]]:
        """Get all configuration profiles"""
        try:
            profiles = []
            response = await self.client.device_management.device_configurations.get()

            if response and response.value:
                for profile in response.value:
                    profiles.append({
                        'id': profile.id,
                        'displayName': profile.display_name,
                        'description': profile.description,
                        'createdDateTime': profile.created_date_time,
                        'lastModifiedDateTime': profile.last_modified_date_time,
                        'version': profile.version
                    })

            return profiles

        except Exception as e:
            logger.error(f"Failed to get configuration profiles: {e}")
            raise

    # =========================================================================
    # Assignment Operations
    # =========================================================================

    async def create_app_assignment(
        self,
        app_id: str,
        target_type: str,
        target_id: Optional[str] = None,
        intent: str = "required",
        **settings
    ) -> bool:
        """
        Create a new app assignment

        Args:
            app_id: Application ID
            target_type: Type of target (group, allDevices, allUsers)
            target_id: Target ID (for group assignments)
            intent: Assignment intent (required, available, uninstall)
            **settings: Additional assignment settings
        """
        try:
            from msgraph.generated.models.mobile_app_assignment import MobileAppAssignment
            from msgraph.generated.models.install_intent import InstallIntent

            assignment = MobileAppAssignment()

            # Set target
            if target_type == "group" and target_id:
                from msgraph.generated.models.group_assignment_target import GroupAssignmentTarget
                target = GroupAssignmentTarget()
                target.odata_type = "#microsoft.graph.groupAssignmentTarget"
                target.group_id = target_id
            elif target_type == "allDevices":
                from msgraph.generated.models.all_devices_assignment_target import AllDevicesAssignmentTarget
                target = AllDevicesAssignmentTarget()
                target.odata_type = "#microsoft.graph.allDevicesAssignmentTarget"
            elif target_type == "allUsers":
                from msgraph.generated.models.all_licensed_users_assignment_target import AllLicensedUsersAssignmentTarget
                target = AllLicensedUsersAssignmentTarget()
                target.odata_type = "#microsoft.graph.allLicensedUsersAssignmentTarget"
            else:
                raise ValueError(f"Invalid target type: {target_type}")

            assignment.target = target

            # Set intent
            assignment.intent = InstallIntent(intent)

            # Set settings
            from msgraph.generated.models.mobile_app_assignment_settings import MobileAppAssignmentSettings
            assignment_settings = MobileAppAssignmentSettings()
            assignment_settings.odata_type = "#microsoft.graph.mobileAppAssignmentSettings"

            # Apply custom settings
            for key, value in settings.items():
                if hasattr(assignment_settings, key):
                    setattr(assignment_settings, key, value)

            assignment.settings = assignment_settings

            # Create assignment
            await self.client.device_app_management.mobile_apps.by_mobile_app_id(
                app_id
            ).assignments.post(assignment)

            return True

        except Exception as e:
            logger.error(f"Failed to create app assignment: {e}")
            raise

    async def delete_app_assignment(self, app_id: str, assignment_id: str) -> bool:
        """Delete an app assignment"""
        try:
            await self.client.device_app_management.mobile_apps.by_mobile_app_id(
                app_id
            ).assignments.by_mobile_app_assignment_id(
                assignment_id
            ).delete()
            return True

        except Exception as e:
            logger.error(f"Failed to delete app assignment: {e}")
            raise

    async def clear_app_assignments(self, app_id: str) -> int:
        """Clear all assignments for an app"""
        try:
            assignments = await self.get_app_assignments(app_id)
            count = 0

            for assignment in assignments:
                await self.delete_app_assignment(app_id, assignment['id'])
                count += 1

            return count

        except Exception as e:
            logger.error(f"Failed to clear app assignments: {e}")
            raise