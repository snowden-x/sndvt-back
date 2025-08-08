## Network Agent Autonomy Plan

A practical roadmap to evolve the current agent into an autonomous, guardrailed network engineer that can plan, chain tools, and act on events using network documentation and telemetry.

### Objectives
- Act autonomously on predictions/events and user intents
- Chain vetted tools (SSH, SNMP, Influx, NetPredict, Ping/Traceroute)
- Reason over a network knowledge graph (devices, interfaces, links, services, departments)
- Enforce safety: RBAC, allow/deny lists, approvals, audit logs
- Produce explainable actions and impact analysis

## Architecture

### Planner
- Rule-first (YAML/JSON SOPs), optional LLM assist later
- Chooses tools, orders steps, injects context (devices/paths from graph)
- Requests approval for risky operations per policy

### Executor
- Runs tools with retries/backoff, captures outputs, metrics, and errors
- Writes step-by-step audit trail (who/what/when/where)
- Persists results to DB (facts, configs, impacts)

### Tool Registry
- BaseTool interface: validate(input), execute(context), metadata(risk, scopes)
- Registry: allow/deny, RBAC scopes, secrets access, rate limits
- Tools (v1): SSHDiscoverTool, SNMPEnrichTool, PingTool, TracerouteTool, InfluxQueryTool, NetPredictClient, TopologyBuilder

### Policies & Modes
- Safe: always ask before device changes or credentials use
- Standard: ask on risky ops, auto-execute read-only
- Autonomous: pre-approved scopes auto-execute, notify

### Memory
- Session memory: last N steps, device context, tool outcomes
- Long-term store: device facts, configs, link graph, past incidents

## Network Knowledge Graph

### Entities
- Devices(id, name, ip, type, os, reachability, last_seen)
- Interfaces(id, device_id, name, descr, status, speed, vlan)
- Links(id, a_device_id, a_if, b_device_id, b_if)
- Services(id, name, endpoints, criticality)
- Departments(id, name, vlan, gateways, endpoints)

### Sources & Ingestion
- Parse `data/network_docs/network_documentation.md` into tables (initial pass)
- Enrich via SNMP: sysName, ifName/ifAlias, LLDP neighbors
- Merge neighbors (SSH/CDP/LLDP) into Links
- Small ETL job to re-sync on doc changes

### Queries (used by planner)
- What depends on interface X? → impacted services/departments
- Path between A and B → devices/interfaces to probe
- Devices for department Y → gateways/DNS/DHCP to check

## Tools (v1)

### SSHDiscoverTool (read-only)
- Inputs: host/ip, username, password or key
- Actions: login, show version/running, LLDP/CDP, basic facts
- Output: device facts, config, neighbor hints
- Side-effects (on confirm): add/update `DeviceInfo`, append to `testbed.yaml`, store config blob

### SNMPEnrichTool (read-only)
- Inputs: host/ip, community or v3 credentials
- Actions: sysName/sysDescr, IF-MIB states/rates, LLDP-MIB neighbors
- Output: interface names/aliases, neighbor edges, health
- Side-effects: update device/ports, add Links

### PingTool / TracerouteTool (read-only)
- Inputs: targets (IPs/hostnames), count/timeout
- Output: reachability metrics, loss/latency, path

### InfluxQueryTool (read-only)
- Inputs: query params (iface, window)
- Output: state transitions, rates, anomalies

### NetPredictClient (read-only)
- Pull predictions and risk scores for devices/interfaces

### TopologyBuilder
- Merge neighbor data into Links; compute impact sets for an interface/device

## Autonomous Flows (SOPs)

### A) Interface Flap Pre-Incident
- Trigger: NetPredict high risk on iface or flap detector event
- Steps:
  1) InfluxQueryTool: recent state and errors
  2) TopologyBuilder: impacted services/departments
  3) Ping/Traceroute: probe critical endpoints
  4) Create enriched alert with recommended next actions

### B) Department Outage Triage
- Trigger: “Engineering cannot access internet”
- Steps:
  1) Graph: resolve dept → VLAN, gateways, DNS/DHCP
  2) PingTool: gateways/DNS/DHCP reachability
  3) InfluxQueryTool: path interface health
  4) Root-cause candidates + remediation steps

### C) Device Discovery Flow
- Trigger: “SSH into 10.0.0.5 with u/p and add”
- Steps:
  1) SSHDiscoverTool: facts + config
  2) Ask: add to devices and testbed? (policy gates)
  3) SNMPEnrichTool: names/links
  4) Update graph; show diff summary

## Background Autonomy
- Subscriptions:
  - NetPredict results → Planner: run Interface Flap SOP
  - Influx flap detector → Planner: same SOP
- Output: Alerts enriched with impact analysis & action summary

## Frontend Enhancements
- Network Chat: session policy toggle (Safe/Standard/Auto)
- Tool run cards: inputs, outputs, duration, status, copy/export
- Suggested actions chips from Planner
- Confirm dialogs with diffs for write operations

## Security & Compliance
- Encrypt credentials at rest; mask in logs
- RBAC per tool/scope; approvals for risky ops
- Rate limit and cooldowns; per-device concurrency caps
- Full audit trail (session, tool, inputs, outputs, user)

## Phased Roadmap

### Milestone 1 (Week 1)
- Tool Registry + BaseTool
- SSHDiscoverTool (read-only) and SNMPEnrichTool
- Minimal DB schema for graph: devices, interfaces, links
- Device discovery chain with confirmation

### Milestone 2 (Week 2)
- InfluxQueryTool and NetPredictClient
- TopologyBuilder + impact queries
- SOP A (Flap Pre-Incident) rule-based planner
- Background job: subscribe to NetPredict + flap detector

### Milestone 3 (Week 3)
- SOP B (Dept Triage) + Ping/Traceroute tools
- Frontend: policy toggles, tool cards, suggested actions
- Audit log views; export transcript

### Milestone 4 (Week 4)
- Hardening: RBAC, approvals, rate limits, credential vault interface
- Optional: LLM-assisted planning/function-calls with RAG over graph/docs

## API & Schema (high-level)
- New endpoints: /agent/tools/run, /agent/plans/execute, /agent/events/subscribe
- Tables: tools_runs, plans_runs, devices, interfaces, links, services, departments
- Background tasks: planner workers for NetPredict/Influx events

## Success Criteria
- Autonomous execution of SOP A on prediction without chat input
- Device discovery adds a new device end-to-end with SNMP enrichment
- Dept outage triage produces a root-cause candidate list within 30s
- All actions auditable, policy-compliant, and explainable

## Open Questions
- Credential storage backend (Fernet vs. external vault)
- Streaming outputs (SSE/WebSocket) for long-running tool runs
- Multi-vendor parsing standardization (TextFSM/NTC vs. Genie/NAPALM)
