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
python setup_device.py
```
This wizard guides you through adding a single device with all configuration options.

#### Option B: Network Discovery
```bash
python discover_network.py
```
This tool scans your network, discovers devices automatically, and helps you add them to monitoring.

#### Option C: Manual Configuration
Edit `device_configs/devices.yaml` directly (see configuration format below).

### 3. Start the Service

```bash
python main.py
```

### 4. Test the System

```bash
python test_device_monitoring.py
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

### Device Management

- `GET /devices/` - List all configured devices
- `GET /devices/{device_id}/status` - Get device status
- `GET /devices/{device_id}/interfaces` - Get all interfaces
- `GET /devices/{device_id}/interfaces/{interface_name}` - Get specific interface
- `GET /devices/{device_id}/health` - Get device health metrics
- `POST /devices/{device_id}/ping` - Ping device
- `GET /devices/{device_id}/test` - Test device connection

### Bulk Operations

- `GET /devices/status/all` - Get status for all devices
- `GET /devices/status/all?device_ids=router1,switch1` - Get status for specific devices

### Discovery

- `GET /devices/discovery/{network}` - Discover devices on network
- `GET /devices/discovery/192.168.1.0/24?snmp_communities=public,private` - Discovery with custom SNMP communities

### Management

- `POST /devices/reload` - Reload device configurations
- `DELETE /devices/cache` - Clear all cache
- `DELETE /devices/cache?device_id=router1` - Clear cache for specific device
- `GET /devices/health` - Service health check

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
curl -X DELETE "http://localhost:8000/devices/cache"
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

## Examples

### Complete Setup Example

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

This completes the device monitoring system setup and provides comprehensive real-time network device integration for your AI assistant! 