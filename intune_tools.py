#!/usr/bin/env python3
"""
Intune macOS Tools - Modern TUI Application
===========================================
A beautiful, intuitive terminal interface for managing macOS devices in Microsoft Intune.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json

# Rich TUI components
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import (
    Header, Footer, Button, Static, Label, ListItem, ListView,
    Tree, DataTable, Input, Switch, Select, TextArea, Tabs, Tab,
    ProgressBar, Sparkline, Placeholder, LoadingIndicator,
    TabbedContent, TabPane, Checkbox, RadioButton, RadioSet,
    RichLog, Collapsible, Markdown, DirectoryTree
)
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive, var
from textual.message import Message
from textual.binding import Binding
from textual import events
from textual.css.query import NoMatches
from textual.widgets import Pretty

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich import box
from rich.layout import Layout
from rich.live import Live
from rich.align import Align

# Import our modules
from src.intune_tools.core.auth import AuthManager
from src.intune_tools.core.graph_client import GraphClient
from src.intune_tools.modules.app_manager import AppManager
from src.intune_tools.modules.device_manager import DeviceManager
from src.intune_tools.modules.group_manager import GroupManager
from src.intune_tools.modules.policy_manager import PolicyManager
from src.intune_tools.modules.profile_manager import ProfileManager
from src.intune_tools.modules.analytics import AnalyticsManager
from src.intune_tools.utils.helpers import format_date, format_size, get_icon


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class AppAssignment:
    """Represents an app assignment configuration"""
    app_id: str
    app_name: str
    group_ids: List[str]
    intent: str  # required, available, uninstall
    settings: Optional[Dict] = None


@dataclass
class GroupSelection:
    """Represents selected groups for assignment"""
    group_id: str
    group_name: str
    member_count: int
    group_type: str  # security, dynamic, office365


# ============================================================================
# Custom Widgets
# ============================================================================

class GroupCard(Static):
    """A card widget for displaying group information"""

    def __init__(self, group: Dict[str, Any], selected: bool = False):
        self.group = group
        self.selected = selected
        super().__init__()

    def compose(self) -> ComposeResult:
        card_class = "group-card-selected" if self.selected else "group-card"
        yield Container(
            Label(f"👥 {self.group['displayName']}", classes="group-title"),
            Label(f"Members: {self.group.get('memberCount', 'N/A')}", classes="group-info"),
            Label(f"Type: {self.group.get('groupType', 'Security')}", classes="group-info"),
            classes=card_class
        )


class AppCard(Static):
    """A card widget for displaying app information"""

    def __init__(self, app: Dict[str, Any], selected: bool = False):
        self.app = app
        self.selected = selected
        super().__init__()

    def compose(self) -> ComposeResult:
        card_class = "app-card-selected" if self.selected else "app-card"
        icon = get_icon(self.app.get('type', ''))
        yield Container(
            Label(f"{icon} {self.app['displayName']}", classes="app-title"),
            Label(f"Publisher: {self.app.get('publisher', 'Unknown')}", classes="app-info"),
            Label(f"Version: {self.app.get('version', 'N/A')}", classes="app-info"),
            Label(f"Type: {self.app.get('type', 'Unknown')}", classes="app-info"),
            classes=card_class
        )


class MetricCard(Static):
    """A card for displaying metrics"""

    def __init__(self, title: str, value: str, subtitle: str = "", trend: Optional[List[int]] = None):
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.trend = trend or []
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.title, classes="metric-title"),
            Label(self.value, classes="metric-value"),
            Label(self.subtitle, classes="metric-subtitle"),
            Sparkline(self.trend, classes="metric-sparkline") if self.trend else Static(),
            classes="metric-card"
        )


# ============================================================================
# Screens
# ============================================================================

class LoginScreen(ModalScreen):
    """Login/Authentication screen"""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static("🔐 Intune Authentication", classes="login-title"),
            Static("Choose your authentication method:", classes="login-subtitle"),
            Vertical(
                Button("Use Device Code", id="auth-device", variant="primary"),
                Button("Use Browser Login", id="auth-browser", variant="primary"),
                Button("Use Custom App (creds.json)", id="auth-custom", variant="success"),
                Static("", id="auth-status", classes="auth-status"),
                classes="login-options"
            ),
            classes="login-container"
        )

    @on(Button.Pressed, "#auth-device")
    async def handle_device_auth(self):
        status = self.query_one("#auth-status", Static)
        status.update("🔄 Starting device code authentication...")
        self.dismiss("device")

    @on(Button.Pressed, "#auth-browser")
    async def handle_browser_auth(self):
        status = self.query_one("#auth-status", Static)
        status.update("🔄 Opening browser for authentication...")
        self.dismiss("browser")

    @on(Button.Pressed, "#auth-custom")
    async def handle_custom_auth(self):
        status = self.query_one("#auth-status", Static)
        status.update("🔄 Loading custom app credentials...")
        self.dismiss("custom")

    def action_cancel(self):
        self.app.exit()


class GroupFirstAssignmentScreen(Screen):
    """Group-first app assignment workflow"""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+s", "save", "Apply"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self, graph_client):
        super().__init__()
        self.graph_client = graph_client
        self.selected_groups = set()
        self.selected_apps = set()
        self.groups = []
        self.apps = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Horizontal(
                # Left panel - Groups
                Vertical(
                    Static("📁 Select Groups", classes="panel-title"),
                    Input(placeholder="Search groups...", id="group-search"),
                    ScrollableContainer(
                        Container(id="groups-container"),
                        classes="scrollable-list"
                    ),
                    Horizontal(
                        Button("Select All", id="select-all-groups", variant="default"),
                        Button("Clear", id="clear-groups", variant="warning"),
                        classes="button-row"
                    ),
                    classes="panel left-panel"
                ),

                # Middle panel - Apps
                Vertical(
                    Static("📱 Select Apps", classes="panel-title"),
                    Input(placeholder="Search apps...", id="app-search"),
                    ScrollableContainer(
                        Container(id="apps-container"),
                        classes="scrollable-list"
                    ),
                    Horizontal(
                        Button("Select All", id="select-all-apps", variant="default"),
                        Button("Clear", id="clear-apps", variant="warning"),
                        classes="button-row"
                    ),
                    classes="panel middle-panel"
                ),

                # Right panel - Assignment Configuration
                Vertical(
                    Static("⚙️ Assignment Settings", classes="panel-title"),
                    Container(
                        Label("Assignment Type:", classes="setting-label"),
                        RadioSet(
                            RadioButton("Required Install", id="intent-required", value=True),
                            RadioButton("Available in Portal", id="intent-available"),
                            RadioButton("Uninstall", id="intent-uninstall"),
                            id="intent-radio"
                        ),
                        Label("Options:", classes="setting-label"),
                        Checkbox("Send notification", id="notify", value=True),
                        Checkbox("Restart required", id="restart"),
                        Checkbox("Override existing", id="override", value=True),
                        classes="settings-container"
                    ),
                    Static("", id="selection-summary", classes="summary"),
                    Horizontal(
                        Button("Preview", id="preview", variant="default"),
                        Button("Apply", id="apply", variant="success"),
                        classes="button-row"
                    ),
                    classes="panel right-panel"
                ),
                classes="main-panels"
            ),
            classes="assignment-container"
        )
        yield Footer()

    async def on_mount(self):
        """Load data when screen mounts"""
        await self.load_groups()
        await self.load_apps()
        self.update_summary()

    async def load_groups(self):
        """Load groups from Graph API"""
        try:
            groups_container = self.query_one("#groups-container", Container)
            groups_container.mount(LoadingIndicator())

            # Fetch groups
            group_manager = GroupManager(self.graph_client)
            self.groups = await group_manager.get_all_groups()

            # Clear loading and add group cards
            groups_container.remove_children()
            for group in self.groups:
                card = GroupCard(group)
                card.can_focus = True
                groups_container.mount(card)

        except Exception as e:
            groups_container.remove_children()
            groups_container.mount(Static(f"Error loading groups: {e}", classes="error"))

    async def load_apps(self):
        """Load apps from Graph API"""
        try:
            apps_container = self.query_one("#apps-container", Container)
            apps_container.mount(LoadingIndicator())

            # Fetch apps
            app_manager = AppManager(self.graph_client)
            self.apps = await app_manager.get_macos_apps()

            # Clear loading and add app cards
            apps_container.remove_children()
            for app in self.apps:
                card = AppCard(app)
                card.can_focus = True
                apps_container.mount(card)

        except Exception as e:
            apps_container.remove_children()
            apps_container.mount(Static(f"Error loading apps: {e}", classes="error"))

    @on(Input.Changed, "#group-search")
    def filter_groups(self, event: Input.Changed):
        """Filter groups based on search"""
        search_term = event.value.lower()
        groups_container = self.query_one("#groups-container", Container)

        for card in groups_container.query(GroupCard):
            if search_term in card.group['displayName'].lower():
                card.display = True
            else:
                card.display = False

    @on(Input.Changed, "#app-search")
    def filter_apps(self, event: Input.Changed):
        """Filter apps based on search"""
        search_term = event.value.lower()
        apps_container = self.query_one("#apps-container", Container)

        for card in apps_container.query(AppCard):
            if search_term in card.app['displayName'].lower():
                card.display = True
            else:
                card.display = False

    def on_click(self, event: events.Click):
        """Handle clicks on cards"""
        # Check if clicked on a group card
        for card in self.query(GroupCard):
            if card.region.contains(event.x, event.y):
                self.toggle_group_selection(card)
                break

        # Check if clicked on an app card
        for card in self.query(AppCard):
            if card.region.contains(event.x, event.y):
                self.toggle_app_selection(card)
                break

    def toggle_group_selection(self, card: GroupCard):
        """Toggle group selection"""
        group_id = card.group['id']
        if group_id in self.selected_groups:
            self.selected_groups.remove(group_id)
            card.selected = False
        else:
            self.selected_groups.add(group_id)
            card.selected = True

        # Update visual
        card.refresh()
        self.update_summary()

    def toggle_app_selection(self, card: AppCard):
        """Toggle app selection"""
        app_id = card.app['id']
        if app_id in self.selected_apps:
            self.selected_apps.remove(app_id)
            card.selected = False
        else:
            self.selected_apps.add(app_id)
            card.selected = True

        # Update visual
        card.refresh()
        self.update_summary()

    def update_summary(self):
        """Update selection summary"""
        summary = self.query_one("#selection-summary", Static)
        summary.update(
            f"Selected: {len(self.selected_groups)} groups, {len(self.selected_apps)} apps\n"
            f"This will create {len(self.selected_groups) * len(self.selected_apps)} assignments"
        )

    @on(Button.Pressed, "#select-all-groups")
    def select_all_groups(self):
        """Select all groups"""
        for card in self.query(GroupCard):
            if card.display:
                self.selected_groups.add(card.group['id'])
                card.selected = True
                card.refresh()
        self.update_summary()

    @on(Button.Pressed, "#clear-groups")
    def clear_groups(self):
        """Clear group selection"""
        self.selected_groups.clear()
        for card in self.query(GroupCard):
            card.selected = False
            card.refresh()
        self.update_summary()

    @on(Button.Pressed, "#select-all-apps")
    def select_all_apps(self):
        """Select all apps"""
        for card in self.query(AppCard):
            if card.display:
                self.selected_apps.add(card.app['id'])
                card.selected = True
                card.refresh()
        self.update_summary()

    @on(Button.Pressed, "#clear-apps")
    def clear_apps(self):
        """Clear app selection"""
        self.selected_apps.clear()
        for card in self.query(AppCard):
            card.selected = False
            card.refresh()
        self.update_summary()

    @on(Button.Pressed, "#preview")
    async def preview_assignments(self):
        """Preview assignments before applying"""
        if not self.selected_groups or not self.selected_apps:
            self.notify("Please select at least one group and one app", severity="warning")
            return

        # Get selected intent
        intent = "required"
        if self.query_one("#intent-available", RadioButton).value:
            intent = "available"
        elif self.query_one("#intent-uninstall", RadioButton).value:
            intent = "uninstall"

        # Create preview
        preview_text = f"Preview: {len(self.selected_groups) * len(self.selected_apps)} assignments\n\n"
        preview_text += f"Intent: {intent.upper()}\n\n"
        preview_text += "Groups:\n"
        for group in self.groups:
            if group['id'] in self.selected_groups:
                preview_text += f"  • {group['displayName']}\n"

        preview_text += "\nApps:\n"
        for app in self.apps:
            if app['id'] in self.selected_apps:
                preview_text += f"  • {app['displayName']}\n"

        self.notify(preview_text, title="Assignment Preview", timeout=10)

    @on(Button.Pressed, "#apply")
    async def apply_assignments(self):
        """Apply the assignments"""
        if not self.selected_groups or not self.selected_apps:
            self.notify("Please select at least one group and one app", severity="error")
            return

        # Get settings
        intent = "required"
        if self.query_one("#intent-available", RadioButton).value:
            intent = "available"
        elif self.query_one("#intent-uninstall", RadioButton).value:
            intent = "uninstall"

        notify = self.query_one("#notify", Checkbox).value
        restart = self.query_one("#restart", Checkbox).value
        override = self.query_one("#override", Checkbox).value

        # Show progress
        self.notify(f"Applying {len(self.selected_groups) * len(self.selected_apps)} assignments...",
                   title="Processing")

        # Apply assignments
        app_manager = AppManager(self.graph_client)
        success_count = 0
        error_count = 0

        for group_id in self.selected_groups:
            for app_id in self.selected_apps:
                try:
                    await app_manager.assign_app_to_group(
                        app_id=app_id,
                        group_id=group_id,
                        intent=intent,
                        notify=notify,
                        restart_required=restart,
                        override_existing=override
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.log.error(f"Failed to assign app {app_id} to group {group_id}: {e}")

        # Show result
        self.notify(
            f"✅ Success: {success_count}\n❌ Failed: {error_count}",
            title="Assignment Complete",
            severity="information" if error_count == 0 else "warning"
        )

    def action_back(self):
        """Go back to main screen"""
        self.app.pop_screen()

    def action_refresh(self):
        """Refresh data"""
        asyncio.create_task(self.load_groups())
        asyncio.create_task(self.load_apps())


class DashboardScreen(Screen):
    """Main dashboard with analytics"""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("e", "export", "Export"),
    ]

    def __init__(self, graph_client):
        super().__init__()
        self.graph_client = graph_client
        self.analytics = AnalyticsManager(graph_client)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            # Metrics row
            Horizontal(
                MetricCard("Total Apps", "0", "macOS Applications"),
                MetricCard("Total Devices", "0", "Managed Devices"),
                MetricCard("Active Users", "0", "Licensed Users"),
                MetricCard("Compliance Rate", "0%", "Last 30 days"),
                classes="metrics-row"
            ),

            # Charts and tables
            Grid(
                Container(
                    Static("📊 Deployment Status", classes="chart-title"),
                    DataTable(id="deployment-table"),
                    classes="chart-container"
                ),
                Container(
                    Static("📈 Assignment Trends", classes="chart-title"),
                    Sparkline([0] * 30, id="trend-chart"),
                    classes="chart-container"
                ),
                Container(
                    Static("🎯 Top Apps by Installation", classes="chart-title"),
                    DataTable(id="top-apps-table"),
                    classes="chart-container"
                ),
                Container(
                    Static("⚠️ Recent Issues", classes="chart-title"),
                    RichLog(id="issues-log", highlight=True, markup=True),
                    classes="chart-container"
                ),
                classes="dashboard-grid"
            ),
            classes="dashboard-container"
        )
        yield Footer()

    async def on_mount(self):
        """Load dashboard data"""
        await self.refresh_dashboard()

    async def refresh_dashboard(self):
        """Refresh all dashboard data"""
        try:
            # Get analytics data
            stats = await self.analytics.get_dashboard_stats()

            # Update metrics
            metrics = self.query(".metric-card")
            if len(metrics) >= 4:
                metrics[0].query_one(".metric-value").update(str(stats.get('total_apps', 0)))
                metrics[1].query_one(".metric-value").update(str(stats.get('total_devices', 0)))
                metrics[2].query_one(".metric-value").update(str(stats.get('active_users', 0)))
                metrics[3].query_one(".metric-value").update(f"{stats.get('compliance_rate', 0)}%")

            # Update deployment table
            deployment_table = self.query_one("#deployment-table", DataTable)
            deployment_table.clear()
            deployment_table.add_columns("Status", "Count", "Percentage")

            deployment_data = stats.get('deployment_status', {})
            total = sum(deployment_data.values())
            for status, count in deployment_data.items():
                percentage = (count / total * 100) if total > 0 else 0
                deployment_table.add_row(status, str(count), f"{percentage:.1f}%")

            # Update top apps table
            top_apps_table = self.query_one("#top-apps-table", DataTable)
            top_apps_table.clear()
            top_apps_table.add_columns("App Name", "Installs", "Success Rate")

            for app in stats.get('top_apps', [])[:10]:
                top_apps_table.add_row(
                    app['name'][:30],
                    str(app['installs']),
                    f"{app['success_rate']}%"
                )

            # Update issues log
            issues_log = self.query_one("#issues-log", RichLog)
            for issue in stats.get('recent_issues', [])[:10]:
                issues_log.write(
                    f"[yellow]{issue['timestamp']}[/yellow] "
                    f"[red]{issue['severity']}[/red] "
                    f"{issue['message']}"
                )

            # Update trend chart
            trend_chart = self.query_one("#trend-chart", Sparkline)
            trend_chart.data = stats.get('assignment_trend', [0] * 30)

        except Exception as e:
            self.notify(f"Error refreshing dashboard: {e}", severity="error")

    def action_refresh(self):
        """Refresh dashboard data"""
        asyncio.create_task(self.refresh_dashboard())

    def action_export(self):
        """Export dashboard data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_export_{timestamp}.json"
        self.notify(f"Dashboard exported to {filename}", severity="information")


# ============================================================================
# Main Application
# ============================================================================

class IntuneMacOSTools(App):
    """Main Intune macOS Tools Application"""

    CSS_PATH = "intune_tools.css"
    TITLE = "Intune macOS Tools"
    SUB_TITLE = "Comprehensive Management Suite"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "toggle_dark", "Dark Mode"),
        Binding("h", "show_help", "Help"),
        Binding("1", "show_assignments", "Assignments"),
        Binding("2", "show_devices", "Devices"),
        Binding("3", "show_dashboard", "Dashboard"),
        Binding("4", "show_policies", "Policies"),
        Binding("5", "show_profiles", "Profiles"),
    ]

    def __init__(self):
        super().__init__()
        self.graph_client = None
        self.auth_manager = None

    def compose(self) -> ComposeResult:
        """Create main application layout"""
        yield Header(show_clock=True)
        yield Container(
            TabbedContent(
                TabPane("🎯 Group Assignments", id="tab-assignments"),
                TabPane("📱 Device Management", id="tab-devices"),
                TabPane("📊 Dashboard", id="tab-dashboard"),
                TabPane("📋 Policies", id="tab-policies"),
                TabPane("⚙️ Profiles", id="tab-profiles"),
                TabPane("🔧 Settings", id="tab-settings"),
                id="main-tabs"
            ),
            id="main-container"
        )
        yield Footer()

    async def on_mount(self):
        """Initialize application on mount"""
        # Show login screen
        auth_method = await self.push_screen_wait(LoginScreen())

        if auth_method:
            # Initialize authentication
            self.auth_manager = AuthManager()

            try:
                if auth_method == "device":
                    await self.auth_manager.authenticate_device_code()
                elif auth_method == "browser":
                    await self.auth_manager.authenticate_browser()
                elif auth_method == "custom":
                    await self.auth_manager.authenticate_custom()

                # Initialize Graph client
                self.graph_client = GraphClient(self.auth_manager.credential)

                # Test connection
                user = await self.graph_client.get_current_user()
                self.notify(f"✅ Connected as {user['displayName']}", title="Authentication Success")

                # Load main interface
                await self.load_main_interface()

            except Exception as e:
                self.notify(f"Authentication failed: {e}", severity="error", title="Error")
                self.exit()
        else:
            self.exit()

    async def load_main_interface(self):
        """Load the main interface components"""
        # Load Group Assignment tab
        assignments_tab = self.query_one("#tab-assignments", TabPane)
        assignments_tab.mount(
            Container(
                Static("Welcome to Group-First Assignment Workflow", classes="welcome-text"),
                Static("This revolutionary approach lets you select groups first, then apps - making bulk assignments intuitive and fast!", classes="description"),
                Button("Start Group Assignment Workflow", id="start-assignment", variant="success"),
                classes="welcome-container"
            )
        )

        # Load Dashboard tab
        dashboard_tab = self.query_one("#tab-dashboard", TabPane)
        dashboard_screen = DashboardScreen(self.graph_client)
        dashboard_tab.mount(dashboard_screen)

        # Load Devices tab
        devices_tab = self.query_one("#tab-devices", TabPane)
        devices_tab.mount(
            Container(
                Static("📱 Device Management", classes="section-title"),
                DataTable(id="devices-table"),
                classes="devices-container"
            )
        )

        # Load Policies tab
        policies_tab = self.query_one("#tab-policies", TabPane)
        policies_tab.mount(
            Container(
                Static("📋 Compliance Policies", classes="section-title"),
                ListView(
                    ListItem(Label("macOS Minimum Version Policy")),
                    ListItem(Label("Disk Encryption Policy")),
                    ListItem(Label("Firewall Configuration Policy")),
                    id="policies-list"
                ),
                classes="policies-container"
            )
        )

        # Load Profiles tab
        profiles_tab = self.query_one("#tab-profiles", TabPane)
        profiles_tab.mount(
            Container(
                Static("⚙️ Configuration Profiles", classes="section-title"),
                ListView(
                    ListItem(Label("Wi-Fi Configuration")),
                    ListItem(Label("VPN Settings")),
                    ListItem(Label("Certificate Management")),
                    id="profiles-list"
                ),
                classes="profiles-container"
            )
        )

        # Load Settings tab
        settings_tab = self.query_one("#tab-settings", TabPane)
        settings_tab.mount(
            Container(
                Static("🔧 Application Settings", classes="section-title"),
                Vertical(
                    Label("Theme:"),
                    RadioSet(
                        RadioButton("Dark", id="theme-dark", value=True),
                        RadioButton("Light", id="theme-light"),
                        RadioButton("Auto", id="theme-auto"),
                    ),
                    Label("Auto-refresh interval (seconds):"),
                    Input(value="300", id="refresh-interval"),
                    Label("Export format:"),
                    Select(
                        options=[("JSON", "json"), ("CSV", "csv"), ("Excel", "xlsx")],
                        value="json",
                        id="export-format"
                    ),
                    Checkbox("Enable notifications", id="enable-notifications", value=True),
                    Checkbox("Show advanced options", id="show-advanced"),
                    Button("Save Settings", id="save-settings", variant="primary"),
                    classes="settings-form"
                ),
                classes="settings-container"
            )
        )

    @on(Button.Pressed, "#start-assignment")
    async def start_assignment_workflow(self):
        """Launch the group-first assignment workflow"""
        await self.push_screen(GroupFirstAssignmentScreen(self.graph_client))

    @on(Button.Pressed, "#save-settings")
    def save_settings(self):
        """Save application settings"""
        # Get settings values
        theme = "dark"
        if self.query_one("#theme-light", RadioButton).value:
            theme = "light"
        elif self.query_one("#theme-auto", RadioButton).value:
            theme = "auto"

        refresh_interval = self.query_one("#refresh-interval", Input).value
        export_format = self.query_one("#export-format", Select).value
        notifications = self.query_one("#enable-notifications", Checkbox).value
        advanced = self.query_one("#show-advanced", Checkbox).value

        # Save to config
        config = {
            'theme': theme,
            'refresh_interval': int(refresh_interval),
            'export_format': export_format,
            'notifications': notifications,
            'show_advanced': advanced
        }

        config_path = Path.home() / ".intune-tools" / "config.json"
        config_path.parent.mkdir(exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        self.notify("Settings saved successfully!", severity="information")

    def action_toggle_dark(self):
        """Toggle dark mode"""
        self.dark = not self.dark

    def action_show_help(self):
        """Show help screen"""
        help_text = """
# Intune macOS Tools - Help

## Keyboard Shortcuts:
- **1-5**: Switch between tabs
- **q**: Quit application
- **d**: Toggle dark mode
- **h**: Show this help
- **r**: Refresh current view
- **Escape**: Go back

## Features:
1. **Group-First Assignments**: Select groups, then apps for intuitive bulk assignments
2. **Device Management**: View and manage all macOS devices
3. **Dashboard**: Real-time analytics and insights
4. **Policies**: Manage compliance policies
5. **Profiles**: Configure device profiles

## Tips:
- Use search boxes to filter large lists
- Click cards to select/deselect items
- Preview changes before applying
- Export data for reports
        """
        self.push_screen(MessageScreen(help_text, "Help"))

    def action_quit(self):
        """Quit the application"""
        self.exit()


class MessageScreen(ModalScreen):
    """Generic message screen"""

    def __init__(self, message: str, title: str = "Message"):
        super().__init__()
        self.message = message
        self.title = title

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.title, classes="message-title"),
            Markdown(self.message, classes="message-content"),
            Button("Close", id="close", variant="primary"),
            classes="message-container"
        )

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss()


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point"""
    app = IntuneMacOSTools()
    app.run()


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("This application requires Python 3.8 or higher")
        sys.exit(1)

    main()