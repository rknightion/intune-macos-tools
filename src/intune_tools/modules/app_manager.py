"""
Application Manager Module
==========================
Handles all app-related operations including assignments.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AppManager:
    """Manages Intune application operations"""

    def __init__(self, graph_client):
        self.client = graph_client

    async def get_macos_apps(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get macOS apps with optional filtering"""
        apps = await self.client.get_macos_apps()

        if filter_criteria:
            apps = self._filter_apps(apps, filter_criteria)

        return apps

    async def assign_app_to_group(
        self,
        app_id: str,
        group_id: str,
        intent: str = "required",
        notify: bool = True,
        restart_required: bool = False,
        override_existing: bool = True
    ) -> bool:
        """
        Assign an app to a specific group

        Args:
            app_id: Application ID
            group_id: Group ID
            intent: Assignment intent (required/available/uninstall)
            notify: Send notification to users
            restart_required: Require restart after installation
            override_existing: Override existing assignments
        """
        try:
            # Check for existing assignments if not overriding
            if not override_existing:
                existing = await self.client.get_app_assignments(app_id)
                for assignment in existing:
                    if assignment['target'].get('groupId') == group_id:
                        logger.info(f"Assignment already exists for app {app_id} to group {group_id}")
                        return True

            # Create assignment
            result = await self.client.create_app_assignment(
                app_id=app_id,
                target_type="group",
                target_id=group_id,
                intent=intent,
                notifications="showAll" if notify else "hideAll",
                restart_required=restart_required
            )

            logger.info(f"Successfully assigned app {app_id} to group {group_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to assign app {app_id} to group {group_id}: {e}")
            raise

    async def bulk_assign_apps(
        self,
        app_ids: List[str],
        group_ids: List[str],
        intent: str = "required",
        **settings
    ) -> Dict[str, Any]:
        """
        Bulk assign multiple apps to multiple groups

        Returns:
            Dictionary with success/failure counts and details
        """
        results = {
            'total': len(app_ids) * len(group_ids),
            'success': 0,
            'failed': 0,
            'errors': []
        }

        for app_id in app_ids:
            for group_id in group_ids:
                try:
                    await self.assign_app_to_group(
                        app_id=app_id,
                        group_id=group_id,
                        intent=intent,
                        **settings
                    )
                    results['success'] += 1

                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'app_id': app_id,
                        'group_id': group_id,
                        'error': str(e)
                    })

        return results

    async def remove_app_assignments(self, app_id: str) -> int:
        """Remove all assignments for an app"""
        return await self.client.clear_app_assignments(app_id)

    async def get_app_installation_status(self, app_id: str) -> Dict[str, Any]:
        """Get installation status for an app across all devices"""
        # This would need additional Graph API endpoints
        # Placeholder for future implementation
        return {
            'installed': 0,
            'pending': 0,
            'failed': 0,
            'not_applicable': 0
        }

    def _filter_apps(self, apps: List[Dict], criteria: Dict) -> List[Dict]:
        """Filter apps based on criteria"""
        filtered = apps

        if 'name' in criteria:
            filtered = [a for a in filtered if criteria['name'].lower() in a['displayName'].lower()]

        if 'publisher' in criteria:
            filtered = [a for a in filtered if criteria['publisher'].lower() in (a.get('publisher') or '').lower()]

        if 'type' in criteria:
            filtered = [a for a in filtered if criteria['type'] in a.get('type', '')]

        if 'has_assignments' in criteria:
            # Would need to fetch assignments for each app
            pass

        return filtered