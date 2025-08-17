---
title: "Building Professional Home Infrastructure: Proxmox + Cloudflare Tunnel + nginx"
date: 2025-08-19T09:00:00-08:00
draft: true
description: "How to build professional-grade home infrastructure using Proxmox VE, Cloudflare tunnels, and nginx reverse proxy for self-hosting AI services and web applications."
tags: ["homelab", "proxmox", "infrastructure", "cloudflare", "nginx", "ai", "self-hosting"]
categories: ["Infrastructure", "DevOps"]
author: "Mark Holton"
showToc: true
TocOpen: false
hidemeta: false
comments: false
disableHLJS: false
disableShare: false
searchHidden: false
cover:
    image: ""
    alt: "Professional Home Infrastructure Architecture"
    caption: "Building enterprise-grade infrastructure at home"
    relative: false
    hidden: false
---

# Building Professional Home Infrastructure: Proxmox + Cloudflare Tunnel + nginx

## Introduction

This post documents how I built a professional-grade home infrastructure using Proxmox VE, Cloudflare tunnels, and nginx reverse proxy. The goal was to create a scalable, secure, and maintainable platform for self-hosting AI services and web applications from home.

## Architecture Overview

The infrastructure follows a multi-layer approach with clear separation of concerns:

```
Internet 
  ↓
Cloudflare Edge (SSL termination, DDoS protection)
  ↓  
Cloudflare Tunnel (secure home connection)
  ↓
nginx Reverse Proxy (routing & load balancing)
  ↓
┌─────────────────────────────────────────┐
│ AI Services    │ Web Apps    │ Admin    │
│ Container 101  │ Container   │ Proxmox  │
│ (Ollama 70B)   │ 103 (API)   │ GUI      │
└─────────────────────────────────────────┘
```

## Hardware Foundation

**Base System**: ASRock AI350 Industrial Mini PC
- **CPU**: AMD Ryzen AI 7 350 APU (8 cores, 16 threads)
- **Memory**: 96GB DDR5-5600 (plenty for AI workloads)
- **Storage**: 1TB NVMe SSD
- **Network**: Dual NIC (1GbE + 2.5GbE)
- **Form Factor**: Compact desktop (117.5 x 110.0 x 49mm)

This hardware provides excellent performance-per-watt for 24/7 home server operation while maintaining a small footprint.

## Network Architecture: Dual NIC Strategy

### Why Two Networks?

Separating management and application traffic provides several benefits:
- **Security**: Admin interfaces isolated from public-facing services
- **Performance**: High-bandwidth AI inference on dedicated 2.5GbE interface
- **Troubleshooting**: Clear separation when diagnosing issues
- **Scalability**: Can optimize each network for its specific workload

### Network Design

```
┌─ Management Network (1GbE) ────────────┐
│ • Proxmox web interface               │
│ • SSH administrative access           │
│ • System monitoring                   │
│ • NAS backup operations               │
│ • IP Range: 192.168.X.0/24           │
└───────────────────────────────────────┘

┌─ Application Network (2.5GbE) ─────────┐
│ • Container services                   │
│ • AI inference traffic                │
│ • User-facing applications            │
│ • External tunnel termination         │
│ • IP Range: 192.168.Y.0/24           │
└───────────────────────────────────────┘
```

## Container Strategy: One Job Per Container

Rather than monolithic containers, I adopted a microservices approach:

### Container 101: AI Inference (Ollama)
- **Purpose**: Large Language Model hosting
- **Technology**: Ollama with Llama 3.1 70B
- **Resources**: 45GB RAM, 6 CPU cores
- **Performance**: ~1.4 tokens/second on CPU inference
- **Network**: Internal access only

### Container 104: nginx Reverse Proxy
- **Purpose**: Internal routing and load balancing
- **Technology**: nginx with custom configurations
- **Resources**: 2GB RAM, 2 CPU cores
- **Features**: Rate limiting, security headers, health checks
- **Network**: Receives traffic from tunnel, routes internally

### Container 107: Cloudflare Tunnel
- **Purpose**: Secure external access
- **Technology**: cloudflared in Docker container
- **Resources**: 1GB RAM, 1 CPU core
- **Benefits**: No port forwarding, DDoS protection, SSL termination
- **Network**: Connects to Cloudflare edge, forwards to nginx

## Why Separate the Tunnel and Proxy?

This was a key architectural decision. Many tutorials combine these services, but separation provides:

**Independent Scaling**: Can restart tunnel without affecting proxy
**Clear Responsibilities**: Tunnel handles external connectivity, proxy handles internal routing
**Better Debugging**: Issues isolated to specific service
**Future Flexibility**: Easy to add multiple tunnels or modify routing

## Security Considerations

### Network Segmentation
- **No Direct External Access**: Only nginx receives external traffic
- **Container Isolation**: Each service on dedicated IP with specific ports
- **Admin Network Separation**: Management traffic isolated from application traffic

### Cloudflare Benefits
- **SSL Termination**: Handled at Cloudflare edge
- **DDoS Protection**: Built-in protection for home connection
- **Zero Trust**: No open ports on home router
- **Geographic Distribution**: Global CDN reduces latency

### Rate Limiting and Access Control
```nginx
# Example nginx configuration (sanitized)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=ai:10m rate=5r/s;

server {
    listen 80;
    server_name api.yourdomain.com;
    
    limit_req zone=api burst=20 nodelay;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://internal-api-server;
        # Additional proxy headers...
    }
}
```

## Deployment Process

### 1. Proxmox Container Creation
```bash
# Create LXC container (Ubuntu 24.04)
pct create 101 local:vztmpl/ubuntu-24.04-standard.tar.zst \
  --memory 46080 \
  --cores 6 \
  --net0 name=eth0,bridge=vmbr1,ip=192.168.Y.101/24 \
  --storage local-lvm:50

pct start 101
```

### 2. Service Installation
Each container follows a standardized setup:
- Ubuntu 24.04 LTS base
- Docker for containerized services
- Systemd for service management
- Standard security hardening

### 3. Cloudflare Tunnel Configuration
```yaml
# config.yml (structure example)
tunnel: your-tunnel-id
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - service: http://nginx-proxy-ip:80
  - service: http_status:404
```

### 4. nginx Routing Configuration
nginx handles all internal routing based on domain names:
- `api.yourdomain.com` → FastAPI application
- `ai.yourdomain.com` → Ollama inference server
- `admin.yourdomain.com` → Proxmox interface
- Health checks and monitoring endpoints

## Performance Characteristics

### AI Inference Performance
- **70B Model Loading**: ~30-60 seconds on first use
- **Simple Queries**: ~9 seconds end-to-end
- **Token Generation**: 1.4 tokens/second (CPU inference)
- **Memory Usage**: 38.6GB under load (85% of allocated)
- **Concurrent Users**: Handles multiple simultaneous requests

### Network Performance
- **2.5GbE Utilization**: Significant headroom for AI workloads
- **Latency**: Sub-10ms container-to-container communication
- **External Access**: Global CDN reduces user latency significantly

## Monitoring and Maintenance

### Health Check Strategy
```bash
# Container health
curl http://nginx-proxy/health
curl http://ai-service/api/tags

# Tunnel connectivity
docker logs cloudflared-tunnel

# Resource monitoring
docker stats
htop
```

### Backup Strategy
- **Container Snapshots**: Daily automated via Proxmox
- **Configuration**: Git repository for all configs
- **Data Volumes**: Rsync to NAS storage
- **Model Storage**: Separate backup for large AI models

## Lessons Learned

### What Worked Well
1. **Separation of Concerns**: Each container having one job simplified debugging
2. **Cloudflare Tunnel**: Eliminated need for port forwarding and VPN
3. **Dual Network**: Clean separation between admin and application traffic
4. **LXC Containers**: Better resource efficiency than VMs for this use case

### What I'd Do Differently
1. **Initial Planning**: More upfront network planning would have saved time
2. **Resource Allocation**: Started conservative, had to resize containers
3. **Documentation**: Document as you build, not after

### Performance Surprises
1. **CPU Inference**: 70B models are surprisingly usable on CPU with enough RAM
2. **Network Overhead**: Negligible impact from proxy layers
3. **Container Density**: Can run many services on single host efficiently

## Cost Considerations

**Hardware**: ~$1,500 for complete system (high-end specs for longevity)
**Operational**: ~$10/month (electricity, internet bandwidth)
**Cloudflare**: Free tier sufficient for personal use
**Software**: All open source (Proxmox, nginx, Ollama, Ubuntu)

Total cost significantly lower than equivalent cloud hosting for AI workloads.

## Future Enhancements

### Planned Additions
- **Container Orchestration**: Consider migrating to Kubernetes
- **GPU Acceleration**: AMD GPU passthrough for faster inference
- **Monitoring Stack**: Prometheus + Grafana for detailed metrics
- **Backup Automation**: Automated offsite backup to cloud storage

### Scaling Considerations
- **Horizontal Scaling**: Multiple AI inference containers
- **Geographic Distribution**: Additional tunnel endpoints
- **Load Balancing**: nginx upstream configurations for zero-downtime deployments

## Conclusion

This infrastructure provides a solid foundation for self-hosting modern applications at home. The combination of Proxmox's enterprise virtualization, Cloudflare's global network, and nginx's proven proxy capabilities creates a professional-grade platform.

Key takeaways:
- **Security**: No open ports, enterprise-grade isolation
- **Performance**: Sufficient for demanding AI workloads
- **Maintainability**: Clear architecture makes updates straightforward
- **Cost-Effective**: Fraction of cloud hosting costs
- **Educational**: Hands-on learning with enterprise technologies

The setup handles everything from AI inference to web applications while maintaining security and performance standards comparable to commercial hosting.

---

*This infrastructure powers both AI research projects and production web applications from a single compact home server. The architecture scales well and provides a solid foundation for expanding into additional services.*

## Technical Specifications Summary

| Component | Specification | Purpose |
|-----------|--------------|---------|
| Host | ASRock AI350 | Compact, efficient home server |
| Hypervisor | Proxmox VE 9.0.3 | Enterprise container/VM management |
| Networking | Dual NIC (1GbE + 2.5GbE) | Traffic segregation |
| External Access | Cloudflare Tunnel | Secure, no-port-forwarding connectivity |
| Reverse Proxy | nginx | Internal routing and load balancing |
| AI Inference | Ollama (70B model) | Local LLM hosting |
| Security | Zero Trust + Container isolation | Defense in depth |

This setup demonstrates that professional infrastructure doesn't require a datacenter—just thoughtful architecture and the right tools.