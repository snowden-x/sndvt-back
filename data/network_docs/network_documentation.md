# Network Infrastructure Documentation

## Document Information
- **Document Version:** 1.0
- **Last Updated:** June 16, 2025
- **Created By:** Network Administrator
- **Review Date:** Quarterly

## Table of Contents
1. [Network Overview](#network-overview)
2. [Network Architecture](#network-architecture)
3. [IP Address Management](#ip-address-management)
4. [Network Equipment](#network-equipment)
5. [Security Configuration](#security-configuration)
6. [Monitoring and Management](#monitoring-and-management)
7. [Troubleshooting Procedures](#troubleshooting-procedures)
8. [Emergency Contacts](#emergency-contacts)

## Network Overview

### Purpose
This document provides comprehensive documentation of our organization's network infrastructure, including hardware specifications, configurations, security policies, and operational procedures.

### Scope
The documentation covers all network components within the corporate headquarters and remote locations, including:
- Core network infrastructure
- Security appliances
- Wireless networks
- WAN connections
- Server networks

### Network Topology Summary
- **Total Sites:** 3 (HQ + 2 branch offices)
- **Total Users:** 250
- **Internet Bandwidth:** 1Gbps (HQ), 100Mbps (branches)
- **Primary ISP:** Acme Internet Services
- **Backup ISP:** Global Connect Solutions

## Network Architecture

### Physical Network Diagram
```
Internet
    |
[Firewall] ── [Core Switch] ── [Distribution Switches]
    |              |                      |
[DMZ Servers]  [Access Switches]    [Wireless APs]
                    |
                [End Devices]
```

### Network Segments

#### Management Network
- **VLAN ID:** 10
- **Subnet:** 192.168.10.0/24
- **Gateway:** 192.168.10.1
- **Purpose:** Network device management

#### Corporate Network
- **VLAN ID:** 20
- **Subnet:** 10.0.20.0/24
- **Gateway:** 10.0.20.1
- **Purpose:** Employee workstations and corporate resources

#### Guest Network
- **VLAN ID:** 30
- **Subnet:** 172.16.30.0/24
- **Gateway:** 172.16.30.1
- **Purpose:** Guest and visitor access

#### Server Network
- **VLAN ID:** 40
- **Subnet:** 10.0.40.0/24
- **Gateway:** 10.0.40.1
- **Purpose:** Internal servers and applications

#### DMZ Network
- **VLAN ID:** 50
- **Subnet:** 203.0.113.0/28
- **Gateway:** 203.0.113.1
- **Purpose:** Public-facing servers

## IP Address Management

### DHCP Pools

| Network | Range | Reserved | Available |
|---------|-------|----------|-----------|
| Corporate | 10.0.20.100-10.0.20.200 | 10.0.20.1-10.0.20.99 | 101 |
| Guest | 172.16.30.100-172.16.30.200 | 172.16.30.1-172.16.30.99 | 101 |

### Static IP Assignments

| Device | IP Address | Purpose |
|--------|------------|---------|
| Core Router | 10.0.1.1 | Primary gateway |
| Core Switch | 192.168.10.10 | Management |
| Firewall Internal | 10.0.1.2 | Security gateway |
| Firewall External | 203.0.113.2 | WAN interface |
| DNS Server 1 | 10.0.40.10 | Primary DNS |
| DNS Server 2 | 10.0.40.11 | Secondary DNS |
| Domain Controller | 10.0.40.20 | Active Directory |
| File Server | 10.0.40.30 | Shared storage |

### DNS Configuration
- **Primary DNS:** 10.0.40.10 (internal)
- **Secondary DNS:** 10.0.40.11 (internal)
- **External DNS:** 8.8.8.8, 1.1.1.1
- **Domain:** company.local

## Network Equipment

### Core Infrastructure

#### Core Router
- **Model:** Cisco ISR 4431
- **Serial Number:** ABC123456789
- **Location:** Main Data Center Rack A1
- **Management IP:** 192.168.10.1
- **Firmware Version:** 16.09.04
- **Configuration Backup:** Daily automated backup to TFTP server

#### Core Switch
- **Model:** Cisco Catalyst 9300-48P
- **Serial Number:** DEF987654321
- **Location:** Main Data Center Rack A1
- **Management IP:** 192.168.10.10
- **Software Version:** 16.12.05
- **Port Configuration:** 48 ports, stacked configuration

#### Firewall
- **Model:** Fortinet FortiGate 200E
- **Serial Number:** GHI456789123
- **Location:** Main Data Center Rack A2
- **Management IP:** 192.168.10.20
- **Firmware Version:** 7.0.5
- **License Status:** Valid until December 2025

### Access Layer Equipment

#### Distribution Switches
| Location | Model | Serial Number | Management IP | Ports |
|----------|-------|---------------|---------------|-------|
| Floor 1 | Cisco C9200-24T | JKL111222333 | 192.168.10.30 | 24 |
| Floor 2 | Cisco C9200-24T | MNO444555666 | 192.168.10.31 | 24 |
| Floor 3 | Cisco C9200-24T | PQR777888999 | 192.168.10.32 | 24 |

#### Wireless Access Points
| Location | Model | Serial Number | Management IP | SSID |
|----------|-------|---------------|---------------|------|
| Reception | Cisco AIR-AP2802I | STU123456 | 192.168.10.50 | CorpWiFi, Guest |
| Conference Room A | Cisco AIR-AP2802I | VWX789012 | 192.168.10.51 | CorpWiFi |
| Open Office Area | Cisco AIR-AP2802I | YZA345678 | 192.168.10.52 | CorpWiFi |

### WAN Connections

#### Primary Internet Connection
- **Provider:** Acme Internet Services
- **Circuit ID:** AIS-12345
- **Bandwidth:** 1Gbps/1Gbps
- **Connection Type:** Fiber Ethernet
- **Public IP Block:** 203.0.113.0/28
- **Support Contact:** 1-800-ACME-ISP

#### Backup Internet Connection
- **Provider:** Global Connect Solutions
- **Circuit ID:** GCS-67890
- **Bandwidth:** 100Mbps/100Mbps
- **Connection Type:** Cable
- **Public IP:** Dynamic (DHCP)
- **Support Contact:** 1-800-GLOBAL-1

## Security Configuration

### Firewall Rules Summary

#### Inbound Rules
1. **Allow HTTPS** - Port 443 to DMZ web servers
2. **Allow SSH** - Port 22 from management network only
3. **Allow VPN** - IPSec and SSL VPN connections
4. **Deny All** - Default deny rule

#### Outbound Rules
1. **Allow HTTP/HTTPS** - Ports 80/443 for web browsing
2. **Allow DNS** - Port 53 to external DNS servers
3. **Allow Email** - Ports 25, 587, 993, 995 for email services
4. **Allow NTP** - Port 123 for time synchronization

### VPN Configuration
- **VPN Type:** SSL VPN and IPSec Site-to-Site
- **SSL VPN Users:** 50 concurrent connections
- **Authentication:** Active Directory integration
- **Split Tunneling:** Disabled
- **Encryption:** AES-256

### Wireless Security
- **Corporate SSID:** WPA3-Enterprise with 802.1X
- **Guest SSID:** WPA2-PSK with captive portal
- **Management:** WPA3-Personal for infrastructure access

## Monitoring and Management

### Network Monitoring Tools
- **Primary NMS:** SolarWinds NPM
- **SNMP Communities:** 
  - Read: monitor123 (changed quarterly)
  - Write: admin456 (changed quarterly)
- **Syslog Server:** 10.0.40.50
- **SNMP Traps:** Enabled on all managed devices

### Backup Procedures
- **Configuration Backups:** Daily automated via TFTP
- **Backup Location:** 10.0.40.60 (Network Backup Server)
- **Retention Policy:** 30 days local, 1 year archive
- **Backup Verification:** Weekly restoration tests

### Performance Baselines
- **Average CPU Utilization:** < 60%
- **Average Memory Utilization:** < 70%
- **Link Utilization:** < 80%
- **Response Time:** < 5ms internal, < 50ms external

## Troubleshooting Procedures

### Common Issues and Solutions

#### Network Connectivity Issues
1. **Check physical connections**
   - Verify cable integrity
   - Check port status lights
   - Test with known good cables

2. **Verify IP configuration**
   ```bash
   ipconfig /all (Windows)
   ip addr show (Linux)
   ```

3. **Test connectivity**
   ```bash
   ping 8.8.8.8
   tracert google.com
   nslookup company.local
   ```

#### Slow Network Performance
1. **Check bandwidth utilization**
2. **Verify QoS policies**
3. **Check for network loops**
4. **Analyze traffic patterns**

#### DHCP Issues
1. **Verify DHCP scope availability**
2. **Check DHCP server status**
3. **Review DHCP reservations and exclusions**
4. **Test DHCP discovery process**

### Escalation Procedures
1. **Level 1:** Help Desk (Internal Extension 1234)
2. **Level 2:** Network Administrator (Extension 5678)
3. **Level 3:** External Network Consultant (1-800-NET-HELP)

## Emergency Contacts

### Internal Contacts
- **IT Director:** John Smith - john.smith@company.com - (555) 123-4567
- **Network Administrator:** Jane Doe - jane.doe@company.com - (555) 234-5678
- **System Administrator:** Bob Johnson - bob.johnson@company.com - (555) 345-6789

### Vendor Support Contacts
- **Cisco TAC:** 1-800-553-2447 (Contract: 12345678)
- **Fortinet Support:** 1-866-648-4638 (Contract: 87654321)
- **ISP Primary Support:** 1-800-ACME-ISP
- **ISP Backup Support:** 1-800-GLOBAL-1

### Critical Procedures
- **Power Outage:** UPS systems provide 30 minutes backup power
- **Internet Outage:** Automatic failover to backup ISP within 5 minutes
- **Security Incident:** Follow incident response plan, contact IT Director immediately

## Change Management

### Change Approval Process
1. **Submit change request** via IT ticketing system
2. **Risk assessment** by network team
3. **Approval** from IT Director for major changes
4. **Implementation** during maintenance window
5. **Post-change verification** and documentation update

### Maintenance Windows
- **Regular Maintenance:** Every Sunday 2:00 AM - 6:00 AM
- **Emergency Maintenance:** As required with 4-hour notice minimum
- **Change Notifications:** All users notified 48 hours in advance

---

**Document Control:**
- This document is reviewed quarterly
- All changes must be approved by the IT Director
- Version history maintained in the IT documentation system