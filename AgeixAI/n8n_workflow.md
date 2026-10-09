# AgeixAISOC — n8n SOAR Workflow Blueprint
# Import this JSON into n8n (http://localhost:5678) to create the SOAR automation.

## Workflow Overview

This workflow receives HITL-approved decisions from AgeixAISOC and executes
SOAR actions on FortiGate via REST API.

```
[Webhook] → [IF Router] → [HTTP Request: FortiGate] → [Respond to Webhook]
                   ↓ (else)
              [Respond to Webhook]
```

## Node Configurations

### 1. Webhook Node
- **Trigger**: Webhook
- **Path**: `/webhook/execute-soar`
- **Options**: Respond to Webhook
- **HTTP Method**: POST
- **Expected payload**:
```json
{
  "decision_id": "DEC-20260720-123456-abc123",
  "action": "approve",
  "analyst": "soc-analyst",
  "notes": "Approved - blocking IP",
  "metadata": {
    "recommended_action": "block_ip",
    "target_ip": "10.0.0.55",
    "mitre_technique": "T1204",
    "risk_score": 85
  },
  "timestamp": "2026-07-20T12:34:56+00:00"
}
```

### 2. IF Node (Action Router)
- **Conditions**:
  - `{{ $json.metadata.recommended_action }}` equals `block_ip`
  - **Route**: true → Execute FortiGate Block
  - **Route**: false → Check next condition

- **Second Condition**:
  - `{{ $json.metadata.recommended_action }}` equals `isolate_host`
  - **Route**: true → Execute FortiGate Isolate

- **Default Route**: Respond "no_action_required"

### 3. HTTP Request Node (Block IP — FortiGate)
- **Method**: POST
- **URL**: `https://{{ $env.FORTIGATE_IP }}/api/v2/cmdb/firewall/address/`
- **Authentication**: Header Auth
  - **Header Name**: `Authorization`
  - **Header Value**: `Bearer {{ $env.FORTIGATE_API_TOKEN }}`
- **Body (JSON)**:
```json
{
  "name": "SOC-Block-{{ $json.metadata.target_ip | replace('.', '_') }}",
  "subnet": "{{ $json.metadata.target_ip }}/32",
  "type": "ipmask",
  "associated-group": "SOC-BLOCKED-IPs",
  "comment": "Blocked by AgeixAISOC - Decision {{ $json.decision_id }}"
}
```

### 4. HTTP Request Node (Isolate Host — FortiGate)
- **Method**: POST
- **URL**: `https://{{ $env.FORTIGATE_IP }}/api/v2/cmdb/firewall/address/`
- **Authentication**: Header Auth
- **Body (JSON)**:
```json
{
  "name": "Quarantine-{{ $json.metadata.target_host | replace('.', '_') }}",
  "subnet": "{{ $json.metadata.target_host }}/32",
  "type": "ipmask",
  "associated-group": "Quarantine_Hosts",
  "comment": "Isolated by AgeixAISOC - Decision {{ $json.decision_id }}"
}
```

### 5. Respond to Webhook Node
- **Respond With**: JSON
```json
{
  "status": "success",
  "decision_id": "{{ $json.decision_id }}",
  "action_executed": "{{ $json.metadata.recommended_action }}",
  "timestamp": "{{ Date.now() }}",
  "message": "SOAR action completed successfully"
}
```

## Environment Variables to Set in n8n

Create these in n8n Settings → Environment Variables:
- `FORTIGATE_IP`: `192.168.56.2`
- `FORTIGATE_API_TOKEN`: `your-fortigate-api-token`

## Testing the Workflow

```bash
curl -X POST http://localhost:5678/webhook/execute-soar \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "DEC-TEST-001",
    "action": "approve",
    "analyst": "test",
    "metadata": {
      "recommended_action": "block_ip",
      "target_ip": "10.0.0.55",
      "mitre_technique": "T1204",
      "risk_score": 85
    }
  }'
```

## Workflow Export JSON

To import: n8n Dashboard → Workflows → Import from File.

```json
{
  "name": "AgeixAISOC - SOAR Execution",
  "nodes": [
    {
      "parameters": {
        "path": "/webhook/execute-soar",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.metadata.recommended_action }}",
              "value2": "block_ip"
            }
          ]
        }
      },
      "name": "IF (Block IP)",
      "type": "n8n-nodes-base.if",
      "position": [450, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "https://{{ $env.FORTIGATE_IP }}/api/v2/cmdb/firewall/address/",
        "authentication": "genericHeader",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $env.FORTIGATE_API_TOKEN }}"
            }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "name",
              "value": "SOC-Block={{ $json.metadata.target_ip | replace('.', '_') }}"
            },
            {
              "name": "subnet",
              "value": "={{ $json.metadata.target_ip }}/32"
            },
            {
              "name": "type",
              "value": "ipmask"
            },
            {
              "name": "associated-group",
              "value": "SOC-BLOCKED-IPs"
            }
          ]
        }
      },
      "name": "FortiGate - Block IP",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "{\"status\":\"success\",\"decision_id\":\"{{ $json.decision_id }}\",\"action_executed\":\"{{ $json.metadata.recommended_action }}\",\"message\":\"SOAR action completed\"}"
      },
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "position": [850, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "IF (Block IP)", "type": "main" }]]
    },
    "IF (Block IP)": {
      "main": [
        [{ "node": "FortiGate - Block IP", "type": "main" }],
        [{ "node": "Respond to Webhook", "type": "main" }]
      ]
    },
    "FortiGate - Block IP": {
      "main": [[{ "node": "Respond to Webhook", "type": "main" }]]
    }
  }
}
```
