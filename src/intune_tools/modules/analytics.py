"""Analytics Manager Module"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random  # For demo data generation

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """Manages analytics and reporting"""

    def __init__(self, graph_client):
        self.client = graph_client

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics"""
        try:
            # Fetch data from various sources
            apps = await self.client.get_macos_apps()
            devices = await self.client.get_macos_devices()
            groups = await self.client.get_all_groups()

            # Calculate statistics
            total_apps = len(apps)
            total_devices = len(devices)
            total_groups = len(groups)

            # Calculate compliance rate
            compliant_devices = sum(1 for d in devices if d.get('complianceState') == 'compliant')
            compliance_rate = round((compliant_devices / total_devices * 100) if total_devices > 0 else 0, 1)

            # Calculate active users (devices with recent sync)
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            active_users = 0

            for device in devices:
                last_sync = device.get('lastSyncDateTime')
                if last_sync:
                    if isinstance(last_sync, str):
                        last_sync = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                    if last_sync > week_ago:
                        active_users += 1

            # Generate deployment status (demo data for now)
            deployment_status = {
                'Installed': random.randint(100, 200),
                'Pending': random.randint(20, 50),
                'Failed': random.randint(5, 15),
                'Not Applicable': random.randint(10, 30)
            }

            # Generate top apps (demo data)
            top_apps = []
            for i, app in enumerate(apps[:10]):
                top_apps.append({
                    'name': app['displayName'],
                    'installs': random.randint(50, total_devices),
                    'success_rate': random.randint(85, 99)
                })

            # Generate assignment trend (demo data - last 30 days)
            assignment_trend = [random.randint(10, 50) for _ in range(30)]

            # Generate recent issues (demo data)
            severities = ['Critical', 'Warning', 'Info']
            issue_messages = [
                'App installation failed on device',
                'Compliance policy violation detected',
                'Device sync timeout',
                'Network connectivity issue during deployment',
                'Insufficient storage for app installation'
            ]

            recent_issues = []
            for i in range(10):
                recent_issues.append({
                    'timestamp': (now - timedelta(hours=random.randint(1, 72))).strftime('%Y-%m-%d %H:%M'),
                    'severity': random.choice(severities),
                    'message': random.choice(issue_messages)
                })

            return {
                'total_apps': total_apps,
                'total_devices': total_devices,
                'active_users': active_users,
                'compliance_rate': compliance_rate,
                'deployment_status': deployment_status,
                'top_apps': top_apps,
                'assignment_trend': assignment_trend,
                'recent_issues': sorted(recent_issues, key=lambda x: x['timestamp'], reverse=True)
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            # Return demo data on error
            return self._get_demo_stats()

    async def get_app_deployment_report(self, app_id: str) -> Dict[str, Any]:
        """Get detailed deployment report for a specific app"""
        # Implementation would fetch app-specific deployment data
        pass

    async def get_device_compliance_report(self) -> Dict[str, Any]:
        """Get device compliance report"""
        devices = await self.client.get_macos_devices()

        compliant = 0
        non_compliant = 0
        unknown = 0

        for device in devices:
            state = device.get('complianceState', 'unknown')
            if state == 'compliant':
                compliant += 1
            elif state == 'noncompliant':
                non_compliant += 1
            else:
                unknown += 1

        return {
            'total_devices': len(devices),
            'compliant': compliant,
            'non_compliant': non_compliant,
            'unknown': unknown,
            'compliance_percentage': round((compliant / len(devices) * 100) if devices else 0, 1)
        }

    async def get_user_activity_report(self, days: int = 30) -> Dict[str, Any]:
        """Get user activity report for the last N days"""
        # Implementation would fetch user activity data
        pass

    async def generate_executive_summary(self) -> str:
        """Generate an executive summary report"""
        stats = await self.get_dashboard_stats()

        summary = f"""
# Intune macOS Management - Executive Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview
- Total macOS Applications: {stats['total_apps']}
- Total Managed Devices: {stats['total_devices']}
- Active Users (Last 7 Days): {stats['active_users']}
- Overall Compliance Rate: {stats['compliance_rate']}%

## Deployment Status
- Successfully Installed: {stats['deployment_status'].get('Installed', 0)}
- Pending Installation: {stats['deployment_status'].get('Pending', 0)}
- Failed Installations: {stats['deployment_status'].get('Failed', 0)}

## Top Applications
{self._format_top_apps(stats['top_apps'][:5])}

## Recent Issues
{self._format_recent_issues(stats['recent_issues'][:5])}

## Recommendations
1. Review failed installations and retry deployment
2. Update non-compliant devices to meet policy requirements
3. Consider automating app assignments for new devices
4. Review and optimize deployment schedules
"""
        return summary

    def _format_top_apps(self, apps: List[Dict]) -> str:
        """Format top apps for report"""
        lines = []
        for i, app in enumerate(apps, 1):
            lines.append(f"{i}. {app['name']} - {app['installs']} installs ({app['success_rate']}% success)")
        return '\n'.join(lines)

    def _format_recent_issues(self, issues: List[Dict]) -> str:
        """Format recent issues for report"""
        lines = []
        for issue in issues:
            lines.append(f"- [{issue['severity']}] {issue['timestamp']}: {issue['message']}")
        return '\n'.join(lines)

    def _get_demo_stats(self) -> Dict[str, Any]:
        """Get demo statistics for testing"""
        return {
            'total_apps': 42,
            'total_devices': 156,
            'active_users': 134,
            'compliance_rate': 87.5,
            'deployment_status': {
                'Installed': 180,
                'Pending': 35,
                'Failed': 12,
                'Not Applicable': 20
            },
            'top_apps': [
                {'name': 'Microsoft Teams', 'installs': 145, 'success_rate': 96},
                {'name': 'Slack', 'installs': 132, 'success_rate': 94},
                {'name': 'Chrome', 'installs': 128, 'success_rate': 98},
                {'name': 'Zoom', 'installs': 125, 'success_rate': 95},
                {'name': 'VS Code', 'installs': 89, 'success_rate': 97}
            ],
            'assignment_trend': [15, 22, 18, 25, 30, 28, 35, 32, 38, 40, 42, 38, 45, 48, 44,
                               50, 52, 48, 55, 58, 54, 60, 62, 58, 65, 68, 64, 70, 72, 75],
            'recent_issues': [
                {'timestamp': '2024-01-15 14:30', 'severity': 'Warning', 'message': 'Deployment throttled due to network'},
                {'timestamp': '2024-01-15 12:15', 'severity': 'Critical', 'message': 'Authentication failure for 3 devices'},
                {'timestamp': '2024-01-15 10:45', 'severity': 'Info', 'message': 'Scheduled maintenance completed'}
            ]
        }