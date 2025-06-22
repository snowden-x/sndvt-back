# Device Monitoring System Guide

## Overview

The device monitoring system provides real-time network device status integration for the SNDVT AI assistant. It supports SNMP, REST API, and SSH monitoring protocols with automatic device discovery capabilities.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Devices

You have three options to add devices:

#### Option A: Interactive Device Setup
```bash
python scripts/setup_device.py
```
This wizard guides you through adding a single device with all configuration options.

#### Option B: Network Discovery
```bash
python scripts/discover_network.py
```
This tool scans your network, discovers devices automatically, and helps you add them to monitoring.

#### Option C: Manual Configuration
Edit `config/device_configs/devices.yaml` directly (see configuration format below).

### 3. Start the Service

```bash
python start_optimized.py
# OR
python -m app.main
```

### 4. Test the System

```bash
python tests/test_device_monitoring.py
```

## Device Configuration Format

### Example devices.yaml

```yaml
devices:
  core-router:
    name: "Core Router"
    host: "192.168.1.1"
    device_type: "router"
    description: "Main network router"
    enabled_protocols: ["snmp", "ssh"]
    timeout: 10
    retry_count: 3
    credentials:
      snmp_community: "public"
      snmp_version: "2c"
      username: "admin"
      # Set password via environment: CORE_ROUTER_PASSWORD=secret

  managed-switch:
    name: "Managed Switch"
    host: "192.168.1.10"
    device_type: "switch"
    description: "24-port managed switch"
    enabled_protocols: ["snmp", "rest"]
    timeout: 5
    retry_count: 2
    credentials:
      snmp_community: "public"
      snmp_version: "2c"
      # Set API token via environment: MANAGED_SWITCH_API_TOKEN=token

global_settings:
  default_timeout: 10
  default_retry_count: 3
  cache_ttl: 300  # 5 minutes
  max_concurrent_queries: 10
```

## API Endpoints

### Device Configuration Management

#### List and View Devices
- `GET /devices/` - List all configured devices
- `GET /devices/{device_id}` - Get specific device configuration
- `GET /devices/{device_id}/config` - Get device configuration details

#### Add and Create Devices
- `POST /devices/` - Add a new device to configuration
- `POST /devices/bulk` - Add multiple devices at once
- `POST /devices/from-discovery` - Add devices from discovery results

#### Edit and Update Devices
- `PUT /devices/{device_id}` - Update entire device configuration
- `PATCH /devices/{device_id}` - Partially update device configuration
- `PUT /devices/{device_id}/credentials` - Update device credentials
- `PATCH /devices/{device_id}/protocols` - Enable/disable protocols

#### Delete Devices
- `DELETE /devices/{device_id}` - Remove device from configuration
- `DELETE /devices/bulk` - Remove multiple devices at once

### Device Monitoring

#### Real-time Status
- `GET /devices/{device_id}/status` - Get current device status
- `GET /devices/{device_id}/health` - Get device health metrics
- `GET /devices/{device_id}/uptime` - Get device uptime information
- `POST /devices/{device_id}/ping` - Ping device and get response time
- `GET /devices/{device_id}/test` - Test all configured protocols

#### Interface Management
- `GET /devices/{device_id}/interfaces` - Get all device interfaces
- `GET /devices/{device_id}/interfaces/{interface_name}` - Get specific interface details
- `GET /devices/{device_id}/interfaces/status` - Get interface status summary
- `POST /devices/{device_id}/interfaces/{interface_name}/reset` - Reset interface counters

#### Performance Metrics
- `GET /devices/{device_id}/metrics` - Get comprehensive device metrics
- `GET /devices/{device_id}/metrics/cpu` - Get CPU usage history
- `GET /devices/{device_id}/metrics/memory` - Get memory usage history
- `GET /devices/{device_id}/metrics/interfaces` - Get interface traffic statistics

### Bulk Operations

#### Status Queries
- `GET /devices/status/all` - Get status for all devices
- `GET /devices/status/all?device_ids=router1,switch1` - Get status for specific devices
- `GET /devices/health/summary` - Get health summary for all devices
- `GET /devices/interfaces/all` - Get interface status for all devices

#### Bulk Actions
- `POST /devices/ping/all` - Ping all devices
- `POST /devices/test/all` - Test connectivity to all devices
- `POST /devices/restart/all` - Restart monitoring for all devices

### Network Discovery

#### Discovery Operations
- `GET /devices/discovery/{network}` - Discover devices on network
- `GET /devices/discovery/{network}?snmp_communities=public,private` - Discovery with custom SNMP communities
- `POST /devices/discovery/scan` - Start custom discovery scan
- `GET /devices/discovery/results/{scan_id}` - Get discovery scan results

#### Discovery Management
- `GET /devices/discovery/history` - Get discovery scan history
- `DELETE /devices/discovery/results/{scan_id}` - Delete discovery results
- `POST /devices/discovery/schedule` - Schedule recurring discovery

### Configuration Management

#### Configuration Operations
- `POST /devices/reload` - Reload device configurations from file
- `POST /devices/validate` - Validate all device configurations
- `GET /devices/config/export` - Export all configurations
- `POST /devices/config/import` - Import device configurations
- `POST /devices/config/backup` - Create configuration backup

#### Template Management
- `GET /devices/templates` - List device configuration templates
- `GET /devices/templates/{template_name}` - Get specific template
- `POST /devices/templates` - Create new device template
- `PUT /devices/templates/{template_name}` - Update device template
- `DELETE /devices/templates/{template_name}` - Delete device template

### Cache Management

#### Cache Operations
- `DELETE /devices/cache` - Clear all cache
- `DELETE /devices/cache?device_id=router1` - Clear cache for specific device
- `DELETE /devices/cache/type/{cache_type}` - Clear specific cache type (status, health, interfaces)
- `GET /devices/cache/stats` - Get cache statistics and hit rates

#### Cache Configuration
- `GET /devices/cache/config` - Get current cache configuration
- `PUT /devices/cache/config` - Update cache settings
- `POST /devices/cache/warm` - Pre-warm cache for all devices

### Credentials Management

#### Credential Operations
- `GET /devices/{device_id}/credentials/test` - Test device credentials
- `POST /devices/{device_id}/credentials/rotate` - Rotate device credentials
- `GET /devices/credentials/status` - Check credential status for all devices

#### Environment Variables
- `GET /devices/env/variables` - List expected environment variables
- `POST /devices/env/validate` - Validate environment variable setup

### Monitoring and Alerts

#### Alert Configuration
- `GET /devices/alerts/rules` - Get monitoring alert rules
- `POST /devices/alerts/rules` - Create new alert rule
- `PUT /devices/alerts/rules/{rule_id}` - Update alert rule
- `DELETE /devices/alerts/rules/{rule_id}` - Delete alert rule

#### Alert Status
- `GET /devices/alerts/active` - Get active alerts
- `GET /devices/alerts/history` - Get alert history
- `POST /devices/alerts/{alert_id}/acknowledge` - Acknowledge alert

### System Health

#### Service Status
- `GET /devices/health` - Service health check
- `GET /devices/health/detailed` - Detailed service health information
- `GET /devices/stats` - Get monitoring statistics
- `GET /devices/version` - Get service version information

#### Performance Monitoring
- `GET /devices/performance` - Get service performance metrics
- `GET /devices/performance/history` - Get performance history
- `POST /devices/performance/benchmark` - Run performance benchmark

## Supported Protocols

### SNMP (Simple Network Management Protocol)

**Best for:** Most network devices (routers, switches, firewalls)

**Configuration:**
```yaml
enabled_protocols: ["snmp"]
credentials:
  snmp_community: "public"
  snmp_version: "2c"  # or "1" or "3"
```

**Capabilities:**
- Interface status and statistics
- Device health (CPU, memory, temperature)
- System information
- Routing table information (Cisco devices)

### REST API

**Best for:** Modern network devices with web APIs

**Configuration:**
```yaml
enabled_protocols: ["rest"]
credentials:
  api_token: "your-token"  # or use environment variable
  # api_key: "your-key"    # alternative
  # username: "admin"      # for basic auth
```

**Capabilities:**
- Device-specific depending on API
- Generally supports all monitoring functions
- Requires device-specific implementation

### SSH (Secure Shell)

**Best for:** Devices accessible via command line

**Configuration:**
```yaml
enabled_protocols: ["ssh"]
credentials:
  username: "admin"
  # password via environment variable
  # ssh_key: "/path/to/key"  # alternative to password
```

**Capabilities:**
- Command execution on devices
- Parsing of CLI output
- Currently implemented as stub (extensible)

## Environment Variables

For security, store sensitive credentials as environment variables:

```bash
# SNMP communities
export DEVICE_ID_SNMP_COMMUNITY=your_community

# Passwords
export DEVICE_ID_PASSWORD=your_password

# API tokens/keys
export DEVICE_ID_API_TOKEN=your_token
export DEVICE_ID_API_KEY=your_key
```

Replace `DEVICE_ID` with your device ID in uppercase with dashes replaced by underscores.

## Network Discovery

### Discovery Process

1. **Ping Sweep** - Tests connectivity to all IPs in range
2. **Port Scan** - Checks common network device ports
3. **Service Detection** - Identifies available protocols
4. **SNMP Probing** - Attempts to get device information
5. **Device Classification** - Suggests device type and protocols

### Discovery Example

```bash
python discover_network.py
```

**Input:**
- Network: `192.168.1.0/24`
- SNMP Communities: `public,private`

**Output:**
- List of discovered devices with suggested configurations
- Option to add selected devices to monitoring

### API Discovery

```bash
curl "http://localhost:8000/devices/discovery/192.168.1.0/24?snmp_communities=public&snmp_communities=private"
```

## API Usage Examples

### Device Configuration Management

#### Adding a New Device
```bash
# Add a single device
curl -X POST "http://localhost:8000/devices/" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "new-router",
    "name": "New Router",
    "host": "192.168.1.1",
    "device_type": "router",
    "description": "Main office router",
    "enabled_protocols": ["snmp", "ssh"],
    "credentials": {
      "snmp_community": "public",
      "snmp_version": "2c",
      "username": "admin"
    },
    "timeout": 10,
    "retry_count": 3
  }'
```

#### Bulk Device Addition
```bash
# Add multiple devices at once
curl -X POST "http://localhost:8000/devices/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [
      {
        "device_id": "router-1",
        "name": "Router 1",
        "host": "192.168.1.1",
        "device_type": "router",
        "enabled_protocols": ["snmp"]
      },
      {
        "device_id": "switch-1",
        "name": "Switch 1", 
        "host": "192.168.1.10",
        "device_type": "switch",
        "enabled_protocols": ["snmp", "rest"]
      }
    ]
  }'
```

#### Updating Device Configuration
```bash
# Update entire device configuration
curl -X PUT "http://localhost:8000/devices/core-router" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Router Name",
    "host": "192.168.1.1",
    "device_type": "router",
    "description": "Updated description",
    "enabled_protocols": ["snmp", "ssh", "rest"],
    "timeout": 15
  }'

# Partially update device (only specific fields)
curl -X PATCH "http://localhost:8000/devices/core-router" \
  -H "Content-Type: application/json" \
  -d '{
    "timeout": 20,
    "retry_count": 5
  }'
```

#### Managing Device Credentials
```bash
# Update device credentials
curl -X PUT "http://localhost:8000/devices/core-router/credentials" \
  -H "Content-Type: application/json" \
  -d '{
    "snmp_community": "private",
    "username": "newadmin",
    "api_token": "new-token-123"
  }'

# Test device credentials
curl "http://localhost:8000/devices/core-router/credentials/test"
```

#### Enabling/Disabling Protocols
```bash
# Enable/disable specific protocols
curl -X PATCH "http://localhost:8000/devices/core-router/protocols" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_protocols": ["snmp", "rest"],
    "disabled_protocols": ["ssh"]
  }'
```

### Device Monitoring Examples

#### Getting Device Status
```bash
# Get comprehensive device status
curl "http://localhost:8000/devices/core-router/status"

# Get device health metrics
curl "http://localhost:8000/devices/core-router/health"

# Get device uptime
curl "http://localhost:8000/devices/core-router/uptime"
```

#### Interface Management
```bash
# Get all interfaces
curl "http://localhost:8000/devices/core-router/interfaces"

# Get specific interface
curl "http://localhost:8000/devices/core-router/interfaces/GigabitEthernet0/1"

# Get interface status summary
curl "http://localhost:8000/devices/core-router/interfaces/status"

# Reset interface counters
curl -X POST "http://localhost:8000/devices/core-router/interfaces/GigabitEthernet0/1/reset"
```

#### Performance Metrics
```bash
# Get comprehensive metrics
curl "http://localhost:8000/devices/core-router/metrics"

# Get CPU usage history
curl "http://localhost:8000/devices/core-router/metrics/cpu"

# Get memory usage history
curl "http://localhost:8000/devices/core-router/metrics/memory"

# Get interface traffic statistics
curl "http://localhost:8000/devices/core-router/metrics/interfaces"
```

### Bulk Operations

#### Status Queries
```bash
# Get status for all devices
curl "http://localhost:8000/devices/status/all"

# Get status for specific devices
curl "http://localhost:8000/devices/status/all?device_ids=router1,switch1,firewall1"

# Get health summary for all devices
curl "http://localhost:8000/devices/health/summary"

# Get interface status for all devices
curl "http://localhost:8000/devices/interfaces/all"
```

#### Bulk Actions
```bash
# Ping all devices
curl -X POST "http://localhost:8000/devices/ping/all"

# Test connectivity to all devices
curl -X POST "http://localhost:8000/devices/test/all"

# Restart monitoring for all devices
curl -X POST "http://localhost:8000/devices/restart/all"
```

### Advanced Discovery

#### Custom Discovery Scans
```bash
# Start custom discovery scan
curl -X POST "http://localhost:8000/devices/discovery/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "network": "192.168.1.0/24",
    "snmp_communities": ["public", "private", "community"],
    "ports": [22, 23, 80, 161, 443],
    "timeout": 5,
    "max_concurrent": 50
  }'

# Get discovery results
curl "http://localhost:8000/devices/discovery/results/scan-123"

# Get discovery history
curl "http://localhost:8000/devices/discovery/history"
```

#### Adding Devices from Discovery
```bash
# Add devices from discovery results
curl -X POST "http://localhost:8000/devices/from-discovery" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "scan-123",
    "device_ips": ["192.168.1.1", "192.168.1.10"],
    "auto_configure": true
  }'
```

### Configuration Management

#### Configuration Operations
```bash
# Validate all configurations
curl -X POST "http://localhost:8000/devices/validate"

# Export all configurations
curl "http://localhost:8000/devices/config/export" > devices_backup.yaml

# Import configurations
curl -X POST "http://localhost:8000/devices/config/import" \
  -H "Content-Type: application/json" \
  -d @devices_backup.yaml

# Create configuration backup
curl -X POST "http://localhost:8000/devices/config/backup"
```

#### Template Management
```bash
# List available templates
curl "http://localhost:8000/devices/templates"

# Get specific template
curl "http://localhost:8000/devices/templates/cisco-router"

# Create new template
curl -X POST "http://localhost:8000/devices/templates" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cisco-switch",
    "device_type": "switch",
    "default_protocols": ["snmp", "ssh"],
    "default_credentials": {
      "snmp_community": "public",
      "snmp_version": "2c"
    }
  }'
```

### Cache Management

#### Cache Operations
```bash
# Get cache statistics
curl "http://localhost:8000/devices/cache/stats"

# Clear specific cache type
curl -X DELETE "http://localhost:8000/devices/cache/type/status"
curl -X DELETE "http://localhost:8000/devices/cache/type/health"
curl -X DELETE "http://localhost:8000/devices/cache/type/interfaces"

# Pre-warm cache for all devices
curl -X POST "http://localhost:8000/devices/cache/warm"
```

#### Cache Configuration
```bash
# Get current cache configuration
curl "http://localhost:8000/devices/cache/config"

# Update cache settings
curl -X PUT "http://localhost:8000/devices/cache/config" \
  -H "Content-Type: application/json" \
  -d '{
    "default_ttl": 300,
    "status_ttl": 30,
    "health_ttl": 60,
    "interface_ttl": 30,
    "max_cache_size": 1000
  }'
```

### PowerShell Examples (Windows)

```powershell
# Add a new device
$deviceData = @{
    device_id = "new-router"
    name = "New Router"
    host = "192.168.1.1"
    device_type = "router"
    enabled_protocols = @("snmp", "ssh")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/devices/" -Method Post -Body $deviceData -ContentType "application/json"

# Get device status
Invoke-RestMethod -Uri "http://localhost:8000/devices/core-router/status"

# Update device configuration
$updateData = @{
    timeout = 20
    retry_count = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/devices/core-router" -Method Patch -Body $updateData -ContentType "application/json"

# Delete device
Invoke-RestMethod -Uri "http://localhost:8000/devices/old-router" -Method Delete
```

## Monitoring Data

### Device Status

```json
{
  "device_id": "core-router",
  "reachable": true,
  "response_time": 15.5,
  "last_seen": 1640995200,
  "health": {
    "cpu_usage": 25.5,
    "memory_usage": 45.2,
    "memory_total": 1024,
    "memory_used": 462,
    "temperature": 42.5,
    "uptime": 86400
  },
  "interfaces": [...],
  "uptime": 86400
}
```

### Interface Information

```json
{
  "name": "GigabitEthernet0/1",
  "description": "WAN Interface",
  "status": "up",
  "admin_status": "up",
  "speed": 1000,
  "mtu": 1500,
  "mac_address": "00:1a:2b:3c:4d:5e",
  "ip_addresses": ["192.168.1.1"],
  "in_octets": 1234567890,
  "out_octets": 987654321,
  "in_errors": 0,
  "out_errors": 0
}
```

## Caching

The system implements intelligent caching to reduce device load:

- **Interface Status**: 30-second cache
- **Health Metrics**: 60-second cache  
- **Device Configuration**: 5-minute cache
- **System Information**: 1-hour cache

Clear cache when needed:
```bash
# Clear all cache
curl -X DELETE "http://localhost:8000/devices/cache"

# Clear cache for specific device
curl -X DELETE "http://localhost:8000/devices/cache?device_id=core-router"

# Clear specific cache type
curl -X DELETE "http://localhost:8000/devices/cache/type/status"
```

## Error Handling

### Connection Issues

- **Device Unreachable**: Returns cached data if available
- **Authentication Failure**: Clear error message with retry logic
- **Timeout**: Configurable timeouts with exponential backoff
- **Protocol Errors**: Graceful fallback to alternative protocols

### Common Issues

1. **SNMP "No Such Instance"**
   - Device doesn't support the requested OID
   - Try different SNMP version or community

2. **SSH Authentication Failed**
   - Check username/password or SSH key
   - Verify environment variables

3. **REST API 401/403**
   - Check API token/key
   - Verify API endpoint URLs

## AI Integration

The monitoring system integrates with the AI assistant through HTTP APIs. The AI can:

1. **Query Device Status**: Get real-time device information
2. **Check Interface Health**: Monitor interface up/down states
3. **Analyze Performance**: Access CPU, memory, and traffic metrics
4. **Troubleshoot Issues**: Correlate device data with user questions

### Example AI Queries

- "What's the status of the core router?"
- "Are there any interfaces down on the network?"
- "Show me the CPU usage of all devices"
- "Which device has the highest memory usage?"

## Extending the System

### Adding New Protocols

1. Create new client class inheriting from `BaseMonitor`
2. Implement required abstract methods
3. Add protocol to device configuration
4. Update service to use new client

### Adding Vendor-Specific Features

1. Extend SNMP client with vendor OIDs
2. Add device-specific parsers
3. Create vendor-specific REST API implementations

### Custom Device Types

1. Add new device type to `DeviceType` enum
2. Update discovery logic for detection
3. Add type-specific monitoring features

## Troubleshooting

### Debug Mode

Set environment variable for verbose logging:
```bash
export DEBUG=1
python main.py
```

### Test Individual Components

```bash
# Test device configuration loading
python -c "from device_monitor.device_manager import DeviceManager; dm = DeviceManager(); print(dm.get_all_devices())"

# Test SNMP connectivity
python -c "from device_monitor.snmp_client import SNMPClient; from device_monitor.base import *; import asyncio; asyncio.run(test_snmp())"

# Test discovery
python -c "from device_monitor.discovery import NetworkDiscovery; import asyncio; asyncio.run(NetworkDiscovery().ping_sweep('127.0.0.1/32'))"
```

### Performance Tuning

1. **Reduce Concurrent Queries**: Lower `max_concurrent_queries` in global settings
2. **Increase Timeouts**: For slow devices, increase timeout values
3. **Optimize Cache TTL**: Balance freshness vs. performance
4. **Limit Discovery Scope**: Use smaller network ranges for discovery

## Security Considerations

1. **Credential Storage**: Use environment variables, not config files
2. **Network Segmentation**: Monitor from management network when possible
3. **SNMP Security**: Use SNMPv3 when available
4. **API Authentication**: Use tokens/keys instead of passwords
5. **Access Control**: Limit monitoring system network access
6. **Audit Logging**: Monitor all device access attempts

## Support

For issues or questions:

1. Check the test script output: `python test_device_monitoring.py`
2. Review device configurations in `device_configs/devices.yaml`
3. Check environment variables for credentials
4. Verify network connectivity to devices
5. Review service logs for error messages

## Common Workflows

### Complete Setup Workflow

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Discover network devices
python discover_network.py
# Enter: 192.168.1.0/24
# Select devices to add

# 3. Add manual device if needed
python setup_device.py
# Follow the wizard

# 4. Set credentials
export CORE_ROUTER_PASSWORD=admin123
export SWITCH_API_TOKEN=abc123

# 5. Start service
python main.py

# 6. Test everything
python test_device_monitoring.py

# 7. Query via API
curl http://localhost:8000/devices/
curl http://localhost:8000/devices/core-router/status
```

### Device Management Workflow

```bash
# 1. Add a new device via API
curl -X POST "http://localhost:8000/devices/" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "new-switch",
    "name": "Office Switch",
    "host": "192.168.1.20",
    "device_type": "switch",
    "enabled_protocols": ["snmp"]
  }'

# 2. Test the new device
curl "http://localhost:8000/devices/new-switch/test"

# 3. Get device status
curl "http://localhost:8000/devices/new-switch/status"

# 4. Update device configuration if needed
curl -X PATCH "http://localhost:8000/devices/new-switch" \
  -H "Content-Type: application/json" \
  -d '{"timeout": 15}'

# 5. Monitor device health
curl "http://localhost:8000/devices/new-switch/health"
```

### Troubleshooting Workflow

```bash
# 1. Check service health
curl "http://localhost:8000/devices/health"

# 2. Get status of all devices
curl "http://localhost:8000/devices/status/all"

# 3. Test connectivity to problematic device
curl -X POST "http://localhost:8000/devices/problem-device/ping"

# 4. Clear cache for fresh data
curl -X DELETE "http://localhost:8000/devices/cache?device_id=problem-device"

# 5. Test device credentials
curl "http://localhost:8000/devices/problem-device/credentials/test"

# 6. Get detailed device information
curl "http://localhost:8000/devices/problem-device/test"
```

### Bulk Operations Workflow

```bash
# 1. Add multiple devices
curl -X POST "http://localhost:8000/devices/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [
      {"device_id": "router-1", "name": "Router 1", "host": "192.168.1.1", "device_type": "router"},
      {"device_id": "switch-1", "name": "Switch 1", "host": "192.168.1.10", "device_type": "switch"}
    ]
  }'

# 2. Test all devices
curl -X POST "http://localhost:8000/devices/test/all"

# 3. Get health summary
curl "http://localhost:8000/devices/health/summary"

# 4. Get interface status for all devices
curl "http://localhost:8000/devices/interfaces/all"
```

### Discovery and Auto-Configuration Workflow

```bash
# 1. Run network discovery
curl "http://localhost:8000/devices/discovery/192.168.1.0/24?snmp_communities=public&snmp_communities=private"

# 2. Start custom discovery scan
curl -X POST "http://localhost:8000/devices/discovery/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "network": "192.168.1.0/24",
    "snmp_communities": ["public", "private"],
    "timeout": 5
  }'

# 3. Get discovery results
curl "http://localhost:8000/devices/discovery/results/scan-123"

# 4. Add discovered devices
curl -X POST "http://localhost:8000/devices/from-discovery" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "scan-123",
    "device_ips": ["192.168.1.1", "192.168.1.10"],
    "auto_configure": true
  }'
```

## Response Formats

### Device Status Response
```json
{
  "device_id": "core-router",
  "name": "Core Router",
  "host": "192.168.1.1",
  "reachable": true,
  "response_time": 15.5,
  "last_seen": 1640995200,
  "status": "online",
  "uptime": 86400,
  "protocols": {
    "snmp": {"available": true, "last_check": 1640995200},
    "ssh": {"available": true, "last_check": 1640995200},
    "rest": {"available": false, "last_check": 1640995200}
  }
}
```

### Device Health Response
```json
{
  "device_id": "core-router",
  "timestamp": 1640995200,
  "health": {
    "cpu_usage": 25.5,
    "memory_usage": 45.2,
    "memory_total": 1024,
    "memory_used": 462,
    "temperature": 42.5,
    "uptime": 86400
  },
  "status": "healthy",
  "alerts": []
}
```

### Interface Response
```json
{
  "device_id": "core-router",
  "interfaces": [
    {
      "name": "GigabitEthernet0/1",
      "description": "WAN Interface",
      "status": "up",
      "admin_status": "up",
      "speed": 1000,
      "mtu": 1500,
      "mac_address": "00:1a:2b:3c:4d:5e",
      "ip_addresses": ["192.168.1.1"],
      "statistics": {
        "in_octets": 1234567890,
        "out_octets": 987654321,
        "in_errors": 0,
        "out_errors": 0,
        "in_discards": 0,
        "out_discards": 0
      }
    }
  ]
}
```

### Discovery Response
```json
{
  "subnet": "192.168.1.0/24",
  "scan_id": "scan-123",
  "timestamp": 1640995200,
  "discovered_devices": [
    {
      "ip": "192.168.1.1",
      "hostname": "router.local",
      "response_time": 15.5,
      "device_type": "router",
      "suggested_protocols": ["snmp", "ssh"],
      "open_ports": [22, 23, 80, 161, 443],
      "system_description": "Cisco IOS Software...",
      "snmp_community": "public"
    }
  ],
  "count": 1
}
```

### Error Response Format
```json
{
  "error": "Device not found",
  "detail": "Device 'invalid-device' is not configured",
  "code": "DEVICE_NOT_FOUND",
  "timestamp": 1640995200
}
```

This completes the comprehensive device monitoring system guide with all necessary endpoints for creating, managing, monitoring, and troubleshooting network devices through the API! 🎉 