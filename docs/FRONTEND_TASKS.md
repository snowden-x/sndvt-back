# Frontend Tasks for Device Monitoring System

## Overview

This document outlines the frontend implementation tasks for the Device Monitoring System. The frontend should provide a web interface for monitoring network devices, managing device configurations, and performing advanced network discovery.

**✅ Backend Status**: All major APIs have been implemented including Device CRUD operations and Advanced Discovery features.

**Backend Setup**: Start the server with:
```bash
python start_optimized.py
# OR
python -m app.main
```
Server will be available at `http://localhost:8000` with API docs at `http://localhost:8000/docs`.

## 🎯 Implementation Priority

### **Phase 1: Core Device Management (Weeks 1-3)**
- Device CRUD operations
- Device list and detail views
- Basic monitoring dashboard

### **Phase 2: Advanced Discovery (Weeks 4-5)**
- Network discovery interface
- Scan management and history
- Device import from discovery

### **Phase 3: Enhanced Monitoring (Weeks 6-7)**
- Real-time status updates
- Interface monitoring
- Health metrics visualization

### **Phase 4: Configuration Management (Weeks 8-9)**
- Bulk operations
- Import/Export functionality
- Configuration templates

## 1. Device Management (CRUD Operations)

### 1.1 Device List/Grid View ✅ **NEW APIs Available**
**Priority: High**

**Tasks:**
- [ ] Device grid with status indicators
- [ ] Add new device button
- [ ] Bulk selection for operations
- [ ] Search and filtering
- [ ] Sort by various fields
- [ ] Device actions menu (edit, delete, duplicate)

**Components:**
- `DeviceGrid`
- `DeviceCard`
- `AddDeviceButton`
- `DeviceFilters`
- `BulkActions`

**API Endpoints:**
```typescript
GET /devices/                          // List all devices
POST /devices/                         // Create new device
POST /devices/bulk                     // Bulk create devices
GET /devices/status/all                // Get status for all devices
```

**Sample Implementation:**
```typescript
interface DeviceCreateRequest {
  name: string;
  host: string;
  device_type: 'router' | 'switch' | 'firewall' | 'access_point' | 'server' | 'generic';
  enabled_protocols: ('snmp' | 'ssh' | 'rest' | 'telnet')[];
  credentials?: {
    snmp_community?: string;
    snmp_version?: string;
    username?: string;
    password?: string;
    ssh_key?: string;
    api_token?: string;
    api_key?: string;
  };
  timeout?: number;
  retry_count?: number;
  description?: string;
}

const DeviceGrid = () => {
  const { data: devices, refetch } = useQuery({
    queryKey: ['devices'],
    queryFn: () => fetch('/api/devices/').then(res => res.json())
  });

  const createDevice = useMutation({
    mutationFn: (device: DeviceCreateRequest) => 
      fetch('/api/devices/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(device)
      }).then(res => res.json()),
    onSuccess: () => refetch()
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1>Network Devices</h1>
        <AddDeviceButton onAdd={createDevice.mutate} />
      </div>
      <DeviceFilters />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {devices?.map(device => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </div>
    </div>
  );
};
```

### 1.2 Device Detail/Edit View ✅ **NEW APIs Available**
**Priority: High**

**Tasks:**
- [ ] Device information display
- [ ] Edit device configuration
- [ ] Delete device with confirmation
- [ ] Test connectivity buttons
- [ ] Configuration validation
- [ ] Save/cancel actions

**Components:**
- `DeviceDetail`
- `DeviceEditForm`
- `CredentialsForm`
- `DeleteConfirmDialog`
- `DeviceActions`

**API Endpoints:**
```typescript
GET /devices/{device_id}              // Get device details
PUT /devices/{device_id}              // Update device
DELETE /devices/{device_id}           // Delete device
POST /devices/{device_id}/ping        // Test connectivity
```

### 1.3 Add/Create Device Form ✅ **NEW APIs Available**
**Priority: High**

**Tasks:**
- [ ] Multi-step device creation wizard
- [ ] Device type selection with icons
- [ ] Protocol configuration
- [ ] Credentials management (secure input)
- [ ] Connection testing before save
- [ ] Form validation and error handling

**Components:**
- `AddDeviceWizard`
- `DeviceTypeSelector`
- `ProtocolConfig`
- `CredentialsForm`
- `ConnectionTest`

## 2. Advanced Network Discovery ✅ **NEW APIs Available**

### 2.1 Discovery Scan Interface
**Priority: High**

**Tasks:**
- [ ] Network range input with CIDR validation
- [ ] Scan type selection (ping, port, full)
- [ ] Advanced options (timeout, concurrency, SNMP communities)
- [ ] Start scan button with progress indicator
- [ ] Real-time scan progress updates

**Components:**
- `DiscoveryForm`
- `NetworkInput`
- `ScanTypeSelector`
- `AdvancedOptions`
- `ScanProgress`

**API Endpoints:**
```typescript
POST /devices/discovery/scan           // Start discovery scan
GET /devices/discovery/scan/{scan_id}  // Get scan status
```

**Sample Implementation:**
```typescript
interface DiscoveryRequest {
  network: string;
  scan_type: 'ping' | 'port' | 'full';
  snmp_communities?: string[];
  ports?: number[];
  timeout?: number;
  max_concurrent?: number;
}

const DiscoveryForm = () => {
  const [scanId, setScanId] = useState<string | null>(null);
  
  const startScan = useMutation({
    mutationFn: (request: DiscoveryRequest) =>
      fetch('/api/devices/discovery/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      }).then(res => res.json()),
    onSuccess: (data) => setScanId(data.scan_id)
  });

  const { data: scanStatus } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => fetch(`/api/devices/discovery/scan/${scanId}`).then(res => res.json()),
    enabled: !!scanId,
    refetchInterval: 2000
  });

  return (
    <div className="space-y-6">
      <DiscoveryFormFields onSubmit={startScan.mutate} />
      {scanStatus && <ScanProgress status={scanStatus} />}
    </div>
  );
};
```

### 2.2 Discovery Results & Device Import ✅ **NEW APIs Available**
**Priority: High**

**Tasks:**
- [ ] Display discovered devices in a table/grid
- [ ] Device information preview (IP, hostname, type, protocols)
- [ ] Confidence score indicators
- [ ] Bulk selection for import
- [ ] Individual device import
- [ ] Auto-add devices functionality

**Components:**
- `DiscoveryResults`
- `DiscoveredDeviceCard`
- `DeviceImportDialog`
- `BulkImportActions`
- `ConfidenceIndicator`

**API Endpoints:**
```typescript
GET /devices/discovery/scan/{scan_id}/results    // Get scan results
POST /devices/discovery/scan/{scan_id}/add-devices // Auto-add discovered devices
```

### 2.3 Scan History & Management ✅ **NEW APIs Available**
**Priority: Medium**

**Tasks:**
- [ ] List of previous discovery scans
- [ ] Scan details and results viewing
- [ ] Delete old scan results
- [ ] Export scan results
- [ ] Scan comparison functionality

**Components:**
- `ScanHistory`
- `ScanHistoryCard`
- `ScanResultsViewer`
- `ScanActions`

**API Endpoints:**
```typescript
GET /devices/discovery/history         // Get scan history
DELETE /devices/discovery/scan/{scan_id} // Delete scan result
POST /devices/discovery/cleanup        // Cleanup old results
```

## 3. Bulk Operations ✅ **NEW APIs Available**

### 3.1 Bulk Device Management
**Priority: Medium**

**Tasks:**
- [ ] Multi-device selection interface
- [ ] Bulk create from CSV/JSON
- [ ] Bulk update operations
- [ ] Bulk delete with confirmation
- [ ] Operation progress tracking

**Components:**
- `BulkOperations`
- `DeviceImporter`
- `BulkEditForm`
- `OperationProgress`

**API Endpoints:**
```typescript
POST /devices/bulk                     // Bulk create devices
```

## 4. Configuration Management ✅ **NEW APIs Available**

### 4.1 Import/Export Configuration
**Priority: Medium**

**Tasks:**
- [ ] Export device configurations to JSON/YAML
- [ ] Import device configurations from file
- [ ] Merge strategy selection (replace, merge, skip existing)
- [ ] Configuration validation before import
- [ ] Backup and restore functionality

**Components:**
- `ConfigExporter`
- `ConfigImporter`
- `MergeStrategySelector`
- `ConfigValidator`

**API Endpoints:**
```typescript
GET /devices/config/export             // Export device configurations
POST /devices/config/import            // Import device configurations
```

**Sample Implementation:**
```typescript
const ConfigManager = () => {
  const exportConfig = useMutation({
    mutationFn: () => fetch('/api/devices/config/export').then(res => res.json()),
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `device-config-${new Date().toISOString()}.json`;
      a.click();
    }
  });

  const importConfig = useMutation({
    mutationFn: (data: { config: any; merge_strategy: string }) =>
      fetch('/api/devices/config/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(res => res.json())
  });

  return (
    <div className="space-y-4">
      <button onClick={() => exportConfig.mutate()}>
        Export Configuration
      </button>
      <ConfigImportForm onImport={importConfig.mutate} />
    </div>
  );
};
```

## 5. Enhanced Monitoring (Existing APIs)

### 5.1 Real-time Device Status
**Priority: High**

**Tasks:**
- [ ] Live status indicators
- [ ] Auto-refresh with configurable intervals
- [ ] Status change notifications
- [ ] Device health metrics display

**Components:**
- `StatusIndicator`
- `HealthMetrics`
- `StatusUpdater`

**API Endpoints:**
```typescript
GET /devices/{device_id}/status       // Device status
GET /devices/{device_id}/health       // Health metrics
GET /devices/{device_id}/interfaces   // Interface status
```

### 5.2 Interface Monitoring
**Priority: Medium**

**Tasks:**
- [ ] Interface status grid
- [ ] Traffic statistics
- [ ] Error rate monitoring
- [ ] Interface configuration display

**Components:**
- `InterfaceGrid`
- `InterfaceCard`
- `TrafficStats`

## 6. Dashboard & Analytics

### 6.1 Main Dashboard
**Priority: High**

**Tasks:**
- [ ] Device status overview cards
- [ ] Network health summary
- [ ] Recent discovery scans
- [ ] Quick actions panel
- [ ] System health indicators

**Components:**
- `Dashboard`
- `StatusOverview`
- `RecentActivity`
- `QuickActions`

### 6.2 Device Analytics
**Priority: Low**

**Tasks:**
- [ ] Device type distribution charts
- [ ] Protocol usage statistics
- [ ] Network topology visualization
- [ ] Performance trends

**Components:**
- `DeviceChart`
- `ProtocolStats`
- `NetworkTopology`

## 7. User Interface & Experience

### 7.1 Layout & Navigation
**Priority: High**

**Tasks:**
- [ ] Responsive sidebar navigation
- [ ] Breadcrumb navigation
- [ ] Global search functionality
- [ ] Theme switcher (dark/light)
- [ ] Mobile-responsive design

**Components:**
- `MainLayout`
- `Sidebar`
- `Header`
- `Breadcrumbs`
- `GlobalSearch`

### 7.2 Forms & Validation
**Priority: High**

**Tasks:**
- [ ] Form validation with real-time feedback
- [ ] Error handling and user feedback
- [ ] Loading states and progress indicators
- [ ] Confirmation dialogs for destructive actions

**Components:**
- `FormField`
- `ValidationMessage`
- `LoadingSpinner`
- `ConfirmDialog`

## 8. Technical Implementation

### 8.1 State Management
```typescript
// Device store with Zustand
interface DeviceStore {
  devices: Device[];
  selectedDevice: Device | null;
  scanHistory: DiscoveryScan[];
  filters: DeviceFilters;
  
  // Actions
  setDevices: (devices: Device[]) => void;
  addDevice: (device: Device) => void;
  updateDevice: (deviceId: string, updates: Partial<Device>) => void;
  deleteDevice: (deviceId: string) => void;
  selectDevice: (device: Device) => void;
  addScan: (scan: DiscoveryScan) => void;
}
```

### 8.2 API Client
```typescript
// Enhanced API client with all endpoints
class DeviceAPI {
  // Device CRUD
  async getDevices(): Promise<Device[]>
  async getDevice(id: string): Promise<Device>
  async createDevice(device: DeviceCreateRequest): Promise<Device>
  async updateDevice(id: string, updates: DeviceUpdateRequest): Promise<Device>
  async deleteDevice(id: string): Promise<void>
  async bulkCreateDevices(devices: DeviceCreateRequest[]): Promise<BulkCreateResponse>
  
  // Discovery
  async startDiscoveryScan(request: DiscoveryRequest): Promise<DiscoveryResponse>
  async getScanStatus(scanId: string): Promise<DiscoveryResponse>
  async getScanResults(scanId: string): Promise<DiscoveryResultResponse>
  async autoAddDevices(scanId: string): Promise<AutoAddResponse>
  async getScanHistory(): Promise<ScanHistoryResponse[]>
  async deleteScanResult(scanId: string): Promise<void>
  
  // Configuration
  async exportConfig(): Promise<DeviceConfigExport>
  async importConfig(config: DeviceConfigImport): Promise<ImportResponse>
  
  // Monitoring (existing)
  async getDeviceStatus(id: string): Promise<DeviceStatus>
  async getAllDeviceStatus(): Promise<Record<string, DeviceStatus>>
  async getDeviceHealth(id: string): Promise<DeviceHealth>
  async getDeviceInterfaces(id: string): Promise<Interface[]>
  async pingDevice(id: string): Promise<PingResponse>
}
```

### 8.3 Type Definitions
```typescript
// Complete type definitions for all API responses
interface Device {
  id: string;
  name: string;
  host: string;
  device_type: DeviceType;
  enabled_protocols: string[];
  credentials: DeviceCredentials;
  timeout: number;
  retry_count: number;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

interface DiscoveryResponse {
  scan_id: string;
  network: string;
  scan_type: string;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  total_hosts: number;
  scanned_hosts: number;
  discovered_devices: DiscoveredDevice[];
  error_message?: string;
}

interface DiscoveredDevice {
  ip: string;
  hostname?: string;
  response_time?: number;
  open_ports: number[];
  suggested_protocols: string[];
  system_description?: string;
  device_type?: string;
  snmp_community?: string;
  confidence_score: number;
}
```

## 9. Testing Strategy

### 9.1 Component Testing
- [ ] Device form validation
- [ ] Discovery scan workflow
- [ ] Bulk operations
- [ ] Configuration import/export

### 9.2 Integration Testing
- [ ] API integration tests
- [ ] End-to-end user workflows
- [ ] Error handling scenarios

### 9.3 Performance Testing
- [ ] Large device list rendering
- [ ] Real-time updates performance
- [ ] Discovery scan handling

## 10. Deployment Considerations

### 10.1 Build Optimization
- [ ] Code splitting for large components
- [ ] Lazy loading for non-critical features
- [ ] Bundle size optimization

### 10.2 Error Handling
- [ ] Global error boundary
- [ ] API error handling
- [ ] Offline state management

---

## 📋 **Quick Start Checklist**

### **Week 1 Goals:**
- [ ] Set up project structure and routing
- [ ] Implement device list with basic CRUD
- [ ] Create device add/edit forms
- [ ] Basic dashboard layout

### **Week 2 Goals:**
- [ ] Discovery scan interface
- [ ] Scan results and device import
- [ ] Bulk operations interface
- [ ] Configuration export/import

### **Week 3 Goals:**
- [ ] Real-time monitoring integration
- [ ] Interface monitoring
- [ ] Polish UI/UX
- [ ] Testing and bug fixes

**🎯 All backend APIs are ready - focus on creating an intuitive and responsive user interface!** 