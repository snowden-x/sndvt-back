# Ansible Integration for Network Engineer Agent

This document describes the Ansible integration that provides the "hands" for the network engineer AI agent, enabling automated network operations and troubleshooting.

## 🎯 Overview

The Ansible integration allows the AI assistant to:
- Execute network automation playbooks
- Perform real-time device health checks
- Troubleshoot connectivity issues
- Backup network configurations
- Configure network devices
- Monitor print servers and other services

## 🏗️ Architecture

### Core Components

1. **AnsibleService** (`app/network_automation/services/ansible_service.py`)
   - Core Ansible execution engine
   - Playbook management and execution
   - Safety validation and risk assessment

2. **PlaybookService** (`app/network_automation/services/playbook_service.py`)
   - High-level network automation tasks
   - Specific operations like health checks, backups, troubleshooting

3. **ToolService** (`app/ai_assistant/services/tool_service.py`)
   - AI tool integration framework
   - Tool calling and execution coordination

4. **API Endpoints** (`app/network_automation/api/playbooks.py`)
   - RESTful API for automation operations
   - Real-time execution monitoring

## 🛠️ Available Tools

### 1. Ping Test
- **Tool**: `ping_test`
- **Purpose**: Test connectivity to network devices
- **Parameters**: `{"target": "hostname_or_ip"}`
- **Example**: "Can you ping the router?"

### 2. Health Check
- **Tool**: `health_check`
- **Purpose**: Comprehensive device health monitoring
- **Parameters**: `{"devices": ["device1", "device2"]}`
- **Example**: "Check the health of all switches"

### 3. Configuration Backup
- **Tool**: `backup_configs`
- **Purpose**: Backup network device configurations
- **Parameters**: `{"devices": ["device1", "device2"]}`
- **Example**: "Backup the router configurations"

### 4. Print Server Check
- **Tool**: `check_print_server`
- **Purpose**: Check print server health and services
- **Parameters**: `{"print_server": "print_server_ip"}`
- **Example**: "Is the print server working?"

### 5. Connectivity Troubleshooting
- **Tool**: `troubleshoot_connectivity`
- **Purpose**: Troubleshoot connectivity between hosts
- **Parameters**: `{"source": "host1", "target": "host2"}`
- **Example**: "Why can't I reach the file server?"

### 6. VLAN Configuration
- **Tool**: `configure_vlans`
- **Purpose**: Configure VLANs across network devices
- **Parameters**: `{"vlan_id": 100, "name": "VLAN_NAME", "devices": ["device1"]}`
- **Example**: "Create VLAN 100 for the engineering team"

## 📁 Ansible Structure

```
ansible/
├── ansible.cfg                 # Ansible configuration
├── inventory/
│   ├── hosts.yml              # Device inventory
│   └── group_vars/            # Group variables
└── playbooks/
    ├── network/
    │   └── backup_configs.yml # Configuration backup
    ├── troubleshooting/
    │   ├── health_check.yml   # Health monitoring
    │   ├── ping_test.yml      # Connectivity testing
    │   └── print_server_check.yml # Print server monitoring
    └── maintenance/
        └── (maintenance playbooks)
```

## 🔄 Workflow Example

### User Request: "Can you check if the print server is working?"

1. **AI Analysis**: AI analyzes the request and identifies it needs the `check_print_server` tool
2. **Tool Execution**: System executes the print server check playbook
3. **Real-time Feedback**: User sees progress updates via WebSocket
4. **Result Analysis**: AI interprets the results and provides insights
5. **Final Response**: Comprehensive status report with recommendations

### API Flow:
```
User Query → AI Analysis → Tool Selection → Playbook Execution → Result Parsing → AI Interpretation → Final Response
```

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Ansible
```bash
# Set up environment variables for credentials
export ANSIBLE_PASSWORD="your_device_password"
export ANSIBLE_ENABLE_PASSWORD="your_enable_password"
```

### 3. Update Inventory
Edit `ansible/inventory/hosts.yml` with your network devices:
```yaml
all:
  children:
    network_devices:
      hosts:
        router1:
          ansible_host: 192.168.1.1
          device_type: router
        switch1:
          ansible_host: 192.168.1.10
          device_type: switch
        print_server:
          ansible_host: 192.168.1.100
          device_type: server
```

### 4. Test Integration
```bash
python test_ansible_integration.py
```

## 🔌 API Endpoints

### Playbook Management
- `POST /api/automation/playbooks/execute` - Execute a playbook
- `GET /api/automation/playbooks/available` - List available playbooks
- `POST /api/automation/playbooks/validate` - Validate playbook safety
- `GET /api/automation/playbooks/status/{execution_id}` - Get execution status

### Network Operations
- `POST /api/automation/backup` - Backup network configurations
- `POST /api/automation/health-check` - Perform health checks
- `POST /api/automation/ping` - Test connectivity
- `POST /api/automation/print-server/check` - Check print server
- `POST /api/automation/troubleshoot` - Troubleshoot connectivity
- `POST /api/automation/vlans/configure` - Configure VLANs

## 🛡️ Safety Features

### 1. Playbook Validation
- AI-powered safety analysis
- Risk level assessment
- Affected host identification
- Warning and recommendation generation

### 2. Execution Monitoring
- Real-time status tracking
- Execution cancellation capability
- Error handling and recovery
- Audit logging

### 3. Access Control
- Environment variable-based credentials
- Network device authentication
- Privilege escalation control

## 🔧 Customization

### Adding New Playbooks
1. Create playbook file in `ansible/playbooks/`
2. Add tool definition in `ToolService._initialize_tools()`
3. Implement execution method in `PlaybookService`
4. Add API endpoint if needed

### Example: Adding a New Tool
```python
# In ToolService._initialize_tools()
"new_tool": Tool(
    name="new_tool",
    description="Description of the new tool",
    parameters={"param1": "string"},
    category="monitoring"
)

# In PlaybookService
async def execute_new_tool(self, parameters: Dict[str, Any]) -> ToolResult:
    # Implementation here
    pass
```

## 🐛 Troubleshooting

### Common Issues

1. **Ansible not found**
   ```bash
   pip install ansible
   ```

2. **Permission denied**
   ```bash
   chmod +x ansible/playbooks/*.yml
   ```

3. **Device connectivity**
   - Verify network connectivity
   - Check credentials in environment variables
   - Ensure SSH access is enabled

4. **Playbook execution fails**
   - Check Ansible logs
   - Verify device inventory
   - Test manual Ansible execution

### Debug Mode
```bash
# Enable verbose Ansible output
export ANSIBLE_VERBOSITY=2
```

## 📈 Performance Optimization

### 1. Parallel Execution
- Multiple playbooks can run concurrently
- Device groups for parallel operations
- Async execution for non-blocking operations

### 2. Caching
- Fact caching for device information
- Result caching for repeated operations
- Connection pooling for SSH sessions

### 3. Resource Management
- Configurable timeouts
- Memory usage monitoring
- Process cleanup on completion

## 🔮 Future Enhancements

### Planned Features
- [ ] Advanced network topology discovery
- [ ] Configuration drift detection
- [ ] Automated remediation workflows
- [ ] Performance baseline monitoring
- [ ] Security policy validation
- [ ] Change impact analysis

### Integration Opportunities
- [ ] Network monitoring systems (SNMP, NetFlow)
- [ ] Configuration management databases (CMDB)
- [ ] Incident management systems
- [ ] Change management workflows
- [ ] Compliance reporting tools

## 📚 Resources

- [Ansible Documentation](https://docs.ansible.com/)
- [Network Automation with Ansible](https://docs.ansible.com/ansible/latest/network/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Network Device Modules](https://docs.ansible.com/ansible/latest/collections/cisco/)

---

This integration transforms your network engineer agent from a knowledge assistant into a powerful automation platform that can actively manage and troubleshoot your network infrastructure. 