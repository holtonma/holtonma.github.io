---
title: "Stabilizing Container Deployments in a Self-Hosted Stack"
date: 2026-02-26T09:00:00-05:00
draft: false
tags: ["docker", "devops", "proxmox", "lxc", "deployment", "infrastructure"]
categories: ["technical-architecture"]
description: "Intermittent container pull failures exposed weak spots in my self-hosted deployment pipeline. This write-up covers diagnosing registry connectivity issues, tightening network configuration, and making deployments more resilient over time."
cover:
    image: "/images/container-deploy-stability.jpg"
    alt: "Whimsical robot repairing a frayed network cable to stabilize a server connection"
    caption: "Reliable systems usually come from small infrastructure fixes compounded over time."
ShowToc: true
TocOpen: false
---

While deploying my Rails app using Kamal, I started seeing intermittent failures pulling containers from GitHub Container Registry (GHCR).

Nothing catastrophic but just enough flakiness to erode trust in automation:

* occasional timeouts during `docker pull`
* inconsistent deploy reliability
* retries sometimes fixing it, sometimes not

These are the kinds of issues worth fixing early to maintain both reliability and velocity. And once you stop trusting deploy automation, velocity drops fast.

![Whimsical robot repairing a frayed network cable to stabilize a server connection](/images/container-deploy-stability.jpg)
*This is the "Hollywood" version for fun. The real work is quieter: logs, retries, and incremental fixes.*

## Deployment Context

The stack:

* Ubuntu 24.04 LTS container host on a self-hosted Proxmox LXC stack (the same container networking issues can show up anywhere).
* Rails app deployed via **Kamal**.
* Container images stored in **GitHub Container Registry (ghcr.io)**.
* [Cloudflare Tunnel]({{< ref "self-hosting-rails-cloudflare-tunnels" >}}) in front of the app.

Deploy flow is:

1. Build image locally / CI
2. Push to GHCR
3. Kamal deploy pulls image to server
4. Container restart through proxy

Reliable container pulls are foundational. If that layer is flaky, the whole deploy pipeline becomes suspect. **Deploys should be boring — consistent, predictable, and repeatable end-to-end**.

## First Diagnostic Step: Confirm It's Network

I ran repeated pulls with a simple script:

```bash
for i in {1..10}; do
  echo "== $i =="
  docker pull ghcr.io/markholton/norafoundry-web:latest && echo OK || echo FAIL
done
```

Early runs showed intermittent failures — sometimes pulls completed instantly, other times they stalled with transport timeouts.

```bash
== 1 ==
latest: Pulling from markholton/norafoundry-web
Digest: sha256:97003258024d123456e55b0485de9d219813e3dc971cc853032e47455e85d6e2
Status: Downloaded newer image
OK

== 2 ==
Error response from daemon:
Get "https://ghcr.io/v2/":
context deadline exceeded
(Client.Timeout exceeded while awaiting headers)

== 3 ==
Error response from daemon:
Head "https://ghcr.io/v2/markholton/norafoundry-web/manifests/latest":
dial tcp 140.82.112.33:443: i/o timeout

== 4 ==
latest: Pulling from markholton/norafoundry-web
Digest: sha256:97003258024d123456e55b0485de9d219813e3dc971cc853032e47455e85d6e2
Status: Image is up to date
OK
```

That ruled out authentication or registry availability issues and pointed toward the network layer instead. After a bit of research, in virtualized home-lab setups the usual culprits are MTU mismatches, "packet fragmentation", or just the extra networking layers virtualization introduces.

> These days it’s incredibly easy to paste an error into an LLM and get useful direction fast. That’s genuinely powerful — I used it during this debugging session myself.
>
> But two things are worth keeping in mind.
>
> First, be mindful of what you share. Logs often contain hostnames, tokens, registry paths, or other operational details you wouldn’t normally publish. Scrub/redact anything sensitive before pasting it anywhere public or semi-public.
>
> Second, treat the AI suggestion as a starting point, not the endpoint. The real value comes from understanding what actually changed and why it worked. That’s how fixes become durable improvements instead of one-off patches.
>
> This post is partly about that: not just fixing a flaky deploy, but understanding the underlying network behavior so the system stays stable going forward.

## The MTU Insight

> MTU (Maximum Transmission Unit) is the largest packet size a network interface will send without breaking it into smaller pieces.
If your system thinks it can send larger packets than the network path actually supports, you can get slowdowns, retransmits, or intermittent timeouts.

In virtualized setups like Proxmox + LXC, packets often pass through extra layers:

* virtual bridges
* container networking
* sometimes overlay or proxy layers

Each layer adds a little header overhead.

The system still reports a default MTU of 1500, but the effective usable MTU can be smaller. If packets exceed that real path limit, they get fragmented or dropped.

That’s when you start seeing symptoms like:

* TCP retransmits (lost packets being resent)
* registry timeouts
* flaky automation

## Applying the Fix Properly

Because this host uses `systemd-networkd`, the MTU must be set in the network unit:

`/etc/systemd/network/eth0.network`

And importantly:

```INI
[Link]
MTUBytes=1450
```

Not under `[Network]`. That distinction matters:

`[Network]` = IP config
`[Link]` = physical interface properties (like MTU)

I initially put it in the wrong section at first and the system silently ignored it.

After correcting:

`systemctl restart systemd-networkd`

MTU persisted and pulls stabilized.

## Result

After the change, 20 consecutive pulls with no timeouts or retries:

```bash
for i in {1..20}; do
  echo "== $i =="
  docker pull ghcr.io/...:latest
done

== 1 ==
latest: Pulling from markholton/norafoundry-web
Digest: sha256:97003258024d123456e55b0485de9d219813e3dc971cc853032e47455e85d6e2
Status: Image is up to date

== 2 ==
latest: Pulling from markholton/norafoundry-web
Digest: sha256:97003258024d123456e55b0485de9d219813e3dc971cc853032e47455e85d6e2
Status: Image is up to date

== 3 ==
latest: Pulling from markholton/norafoundry-web
Digest: sha256:97003258024d123456e55b0485de9d219813e3dc971cc853032e47455e85d6e2
Status: Image is up to date

== 4 ==
latest: Pulling from markholton/norafoundry-web
Digest: sha256:97003258024d123456e55b0485de9d219813e3dc971cc853032e47455e85d6e2
Status: Image is up to date
```

No more flaky pulls, and the deploy was humming again.

## While We Are Here

Should also tighten a few other things:

* enabled SSH key-only authentication (stronger cryptographic auth, no shared secrets)
* disabled password SSH logins (prevents credential-guessing attacks, bots hammer password auth constantly)
* improved deployment hooks to skip redundant binary uploads (don't upload if it is already there)

All small steps toward deterministic automation and lower cognitive load.

## Why This Matters

If you run your own infrastructure, you don't just ship apps. You build:

* reliability
* repeatability
* operational confidence

Infrastructure improvements compound quietly. Small stability fixes today prevent bigger operational headaches later.

## Closing Thought

I'm building Nora Foundry and KEEP as long-term software projects. Stable deployment plumbing makes a big difference in maintaining velocity and consistency.

A lot of the work isn’t glamorous. But it’s exactly the work that keeps everything else moving smoothly.
