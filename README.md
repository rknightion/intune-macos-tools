# Intune macOS Tools Suite

A comprehensive, modern toolkit for managing macOS devices in Microsoft Intune with an intuitive Terminal User Interface (TUI) and powerful automation capabilities.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-lightgrey.svg)

## 🚀 Features

### Revolutionary Group-First Assignment Workflow
Unlike the native Intune UI that forces you to assign apps one by one, our tool lets you:
1. **Select groups first** - Choose multiple groups at once
2. **Select apps** - Pick all the apps you want to assign
3. **Configure once** - Set assignment settings (required/available/uninstall)
4. **Deploy to all** - Apply assignments to all selected groups × apps in one operation

### Beautiful Terminal User Interface
- **Modern TUI** built with Textual framework
- **Responsive design** that works in any terminal
- **Keyboard navigation** for power users
- **Rich visualizations** including charts, tables, and progress indicators
- **Dark/Light themes** with automatic detection

### Comprehensive Module Suite

#### 📱 App Management
- List and filter macOS applications
- Bulk assign apps to multiple groups
- Group-first assignment workflow
- Assignment preview and dry-run
- Backup and restore assignments

#### 💻 Device Management
- View all macOS devices
- Check compliance status
- Remote actions (sync, restart, lock, wipe)
- Device statistics and analytics
- User-device mapping

#### 👥 Group Management
- View all Azure AD groups
- Member management
- Dynamic group support
- Group statistics
- Bulk operations

#### 📋 Compliance Policies
- Create and manage compliance policies
- macOS-specific policy templates
- Policy assignment to groups
- Compliance reporting

#### ⚙️ Configuration Profiles
- Wi-Fi, VPN, and certificate profiles
- Restriction policies
- Profile templates
- Bulk deployment

#### 📊 Analytics Dashboard
- Real-time statistics
- Deployment status tracking
- Compliance metrics
- Trend analysis
- Executive reports

## 🎯 Why This Tool?

### Problems with Native Intune UI
- **Tedious app-by-app assignment** - You have to open each app individually
- **No bulk operations** - Can't select multiple apps at once
- **Poor visualization** - Hard to see overall assignment status
- **Limited filtering** - Difficult to find specific apps or groups
- **No backup/restore** - Can't save assignment configurations

### Our Solution
- **Group-first workflow** - Select groups, then apps - intuitive and fast
- **Bulk everything** - Select multiple items and apply operations to all
- **Rich visualizations** - See everything at a glance
- **Advanced filtering** - Find what you need instantly
- **Configuration management** - Save, backup, and restore assignments

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Microsoft Intune subscription
- Azure AD admin access (for initial setup)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/intune-macos-tools.git
cd intune-macos-tools
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python intune_tools.py
```

## 🔐 Authentication

### Method 1: Interactive (Default)
Uses Microsoft's public Graph PowerShell app. No setup required.

### Method 2: Custom App Registration (Recommended)
For production use with better security and audit trail.

1. Create an app registration in Azure AD
2. Grant required permissions:
   - DeviceManagementApps.ReadWrite.All
   - DeviceManagementManagedDevices.ReadWrite.All
   - Group.Read.All
   - User.Read.All

3. Create `creds.json`:
```json
{
  "appId": "your-app-id",
  "tenantId": "your-tenant-id",
  "clientSecret": "your-secret"
}
```

## 🎮 Usage

### Terminal User Interface (TUI)

Launch the beautiful TUI:
```bash
python intune_tools.py
```

Navigate with:
- **Tab/Shift+Tab** - Move between elements
- **Enter** - Select/activate
- **Space** - Toggle checkboxes
- **Arrow keys** - Navigate lists
- **1-5** - Quick switch between modules
- **q** - Quit
- **d** - Toggle dark mode
- **h** - Help

### Command Line Interface (CLI)

For automation and scripting:

```bash
# List all macOS apps
python intune_tools.py list-apps

# Assign apps to groups
python intune_tools.py assign --apps app1,app2 --groups group1,group2 --intent required

# Backup current assignments
python intune_tools.py backup

# Generate analytics report
python intune_tools.py report --format html
```

## 🌟 Key Workflows

### Group-First App Assignment

1. **Launch the tool** and authenticate
2. **Navigate to Group Assignments** (Press 1)
3. **Select your groups** - Use search to filter, click to select multiple
4. **Select your apps** - Again, search and multi-select
5. **Configure settings** - Choose required/available/uninstall
6. **Preview** - See what will be changed
7. **Apply** - Execute all assignments at once

This workflow that would take hours in the native UI takes minutes with our tool!

### Bulk Operations Example

```python
# Traditional Intune UI workflow (tedious):
# 1. Open App 1 → Add assignment → Select Group 1 → Save
# 2. Open App 1 → Add assignment → Select Group 2 → Save
# 3. Open App 2 → Add assignment → Select Group 1 → Save
# 4. Open App 2 → Add assignment → Select Group 2 → Save
# ... repeat for each app × group combination

# Our tool (efficient):
# 1. Select Groups: [Group 1, Group 2]
# 2. Select Apps: [App 1, App 2]
# 3. Click Apply
# Done! All 4 assignments created at once
```

## 📊 Dashboard Features

The analytics dashboard provides:

- **Real-time metrics** - Apps, devices, users, compliance
- **Deployment tracking** - Success/failure rates
- **Trend analysis** - Historical data visualization
- **Top apps** - Most deployed applications
- **Issue tracking** - Recent problems and alerts
- **Export capabilities** - Generate reports in multiple formats

## 🔧 Advanced Features

### Configuration Management
- Save settings to `~/.intune-tools/config.json`
- Authentication caching for faster subsequent runs
- Customizable refresh intervals
- Export format preferences

### Backup and Restore
```bash
# Create backup
python intune_tools.py backup

# Restore from backup
python intune_tools.py restore backup_20240115.json
```

### Filtering and Search
- Regex pattern matching for names
- Filter by publisher, type, or status
- Complex queries with multiple criteria
- Save filter presets

## 🛠️ Development

### Project Structure
```
intune-macos-tools/
├── intune_tools.py          # Main TUI application
├── intune_tools.css         # Textual styling
├── src/
│   └── intune_tools/
│       ├── core/           # Core functionality
│       │   ├── auth.py     # Authentication manager
│       │   └── graph_client.py  # Graph API client
│       ├── modules/        # Feature modules
│       │   ├── app_manager.py
│       │   ├── device_manager.py
│       │   ├── group_manager.py
│       │   ├── policy_manager.py
│       │   ├── profile_manager.py
│       │   └── analytics.py
│       └── utils/          # Utilities
│           └── helpers.py
├── requirements.txt
└── README.md
```

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black .
pylint src/
```

## 🚦 Roadmap

- [x] Modern TUI with Textual
- [x] Group-first assignment workflow
- [x] Device management module
- [x] Compliance policies
- [x] Configuration profiles
- [x] Analytics dashboard
- [ ] Web-based dashboard
- [ ] Automated deployment schedules
- [ ] AI-powered recommendations
- [ ] Slack/Teams integration
- [ ] Multi-tenant support

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Microsoft Graph SDK team
- Textual framework developers
- Rich library for beautiful terminal output
- The Intune community for feedback and ideas

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/intune-macos-tools/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/intune-macos-tools/discussions)
- **Email**: support@example.com

## ⚠️ Disclaimer

This tool modifies Intune configurations which can affect device functionality. Always:
- Test in a development environment first
- Create backups before bulk operations
- Use dry-run mode to preview changes
- Have a rollback plan

---

**Made with ❤️ for the Intune community**

*Turning hours of clicking into seconds of productivity*