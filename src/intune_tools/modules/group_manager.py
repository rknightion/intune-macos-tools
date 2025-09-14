"""Group Manager Module"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GroupManager:
    """Manages group-related operations"""

    def __init__(self, graph_client):
        self.client = graph_client

    async def get_all_groups(self) -> List[Dict[str, Any]]:
        """Get all groups"""
        return await self.client.get_all_groups()

    async def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """Get members of a group"""
        return await self.client.get_group_members(group_id)

    async def get_dynamic_groups(self) -> List[Dict[str, Any]]:
        """Get only dynamic groups"""
        groups = await self.get_all_groups()
        return [g for g in groups if 'DynamicMembership' in g.get('groupTypes', [])]

    async def get_security_groups(self) -> List[Dict[str, Any]]:
        """Get only security groups"""
        groups = await self.get_all_groups()
        return [g for g in groups if g.get('securityEnabled')]

    async def get_groups_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get groups that a user is member of"""
        # Implementation would fetch user's groups
        pass

    async def create_group(
        self,
        display_name: str,
        description: str,
        mail_nickname: str,
        security_enabled: bool = True,
        mail_enabled: bool = False
    ) -> Dict[str, Any]:
        """Create a new group"""
        # Implementation would create group
        pass

    async def add_member_to_group(self, group_id: str, member_id: str) -> bool:
        """Add a member to a group"""
        # Implementation would add member
        pass

    async def remove_member_from_group(self, group_id: str, member_id: str) -> bool:
        """Remove a member from a group"""
        # Implementation would remove member
        pass

    async def get_group_statistics(self) -> Dict[str, Any]:
        """Get group statistics"""
        groups = await self.get_all_groups()

        total = len(groups)
        security = sum(1 for g in groups if g.get('securityEnabled'))
        mail_enabled = sum(1 for g in groups if g.get('mailEnabled'))
        dynamic = sum(1 for g in groups if 'DynamicMembership' in g.get('groupTypes', []))

        # Calculate member distribution
        member_counts = []
        for group in groups:
            count = group.get('memberCount', 0)
            member_counts.append(count)

        avg_members = sum(member_counts) / len(member_counts) if member_counts else 0
        max_members = max(member_counts) if member_counts else 0
        min_members = min(member_counts) if member_counts else 0

        return {
            'total': total,
            'security_groups': security,
            'mail_enabled_groups': mail_enabled,
            'dynamic_groups': dynamic,
            'static_groups': total - dynamic,
            'average_members': round(avg_members, 1),
            'max_members': max_members,
            'min_members': min_members,
            'total_members': sum(member_counts)
        }