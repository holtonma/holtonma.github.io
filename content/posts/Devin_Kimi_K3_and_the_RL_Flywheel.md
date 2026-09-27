---
title: "Devin, Kimi K3, and the RL Flywheel Behind a Coding Agent"
date: 2026-09-27T14:09:00-04:00
draft: false
tags: ["AI", "Coding Agents", "Devin", "Kimi K3", "Reinforcement Learning", "LLM", "Claude Code"]
categories: ["ai-architecture", "technical-deep-dive"]
description: "I explore how Cognition used coding-focused RL to build SWE-2 from Moonshot’s open-weight Kimi K3, where Devin’s harness fits in, and how its cost compares with Claude Code."
author: "Mark Holton"
cover:
    image: "/images/moonshot-kimi-devin-hero.jpg"
    alt: "Whimsical robots on a crescent moon tuning dials on an RL Training Box while a MarkBot reads a scroll of equations and an engineer works nearby"
    caption: "Moonshot's model, Cognition's RL training, and a human still making the final call."
ShowToc: true
TocOpen: false
math: true
---

We all have used Claude Code to work through engineering problems and tasks. I can point it at a repository, inspect its reasoning and edits, redirect it, and decide what to ship.

Devin can do similar work, but its workflow is slightly different and interesting. Let's say I have a steady stream of bounded improvements to make to [KEEP Terminal](https://getkeep.app/). I can hand over one issue at a time, receive a tested pull request, and ask a review agent to examine it before I make the final call, and [Devin Review](https://docs.devin.ai/work-with-devin/devin-review) supports that review step.

While exploring and adapting a bit to that workflow, I found myself asking more interesting technical questions about the models and harnesses at Cognition. The company behind Devin has developed SWE-2, a coding model derived from Moonshot AI’s Kimi K3. It uses reinforcement learning (RL) to improve the model on software tasks and an agent harness to put that model to work. Where, exactly, does the improvement come from?

![Whimsical robots on a crescent moon tuning dials on an RL Training Box while a MarkBot reads a scroll of equations and an engineer works nearby](/images/moonshot-kimi-devin-hero.jpg)
*A whimsical view of Kimi K3 feeding an RL training process: coding attempts and test feedback guide many small weight updates, producing a model better suited to software engineering.*

## First, what is Devin?

Devin is Cognition’s software engineering agent platform. Connect a repository, describe a task, and an agent can explore the code, edit it, run commands and tests, and prepare a pull request for review. Like Anthropic and OpenAI before them, Cognition offers web, desktop, and CLI experiences, along with integrations for places where engineering requests originate, including Slack, Linear, and Jira. Its own account of using Devin internally emphasizes specific tasks, clear success criteria, and human review of the resulting PR. [Cognition: How Cognition Uses Devin to Build Devin](https://cognition.com/blog/how-cognition-uses-devin-to-build-devin) · [Anthropic: Claude Code on desktop](https://www.anthropic.com/news/claude-opus-4-5) · [OpenAI: Codex app](https://openai.com/index/introducing-the-codex-app/)

The useful distinction between Devin and its predecessors is one of **emphasis**, not a bright line between “autonomous” and “interactive.” Devin packages task intake, repository context, delegated cloud work, and review as a team workflow. Claude Code is especially natural when I want to work alongside the agent in my development environment, although it can also run away from my laptop. [Anthropic: Claude Code overview](https://code.claude.com/docs/en/overview)

### The cost question: what does $20 buy?

As of September 27, Devin lists Pro at **$20/month** and Claude lists Pro at **$20/month when billed monthly**; both include their respective coding agents. Yet neither publishes a simple, comparable “you get N tokens a month” allowance for these subscriptions. Devin describes a daily and weekly quota measured against model-dependent token costs. Anthropic describes shared Claude and Claude Code usage limits whose consumption varies with model, context, and effort. I therefore **cannot verify that Devin Pro gives more included tokens than Claude Pro for the same $20**. Counting tokens alone would also miss whether a model solves the task with fewer turns. [Devin pricing](https://devin.ai/pricing) · [Devin quota documentation](https://docs.devin.ai/desktop/accounts/quota) · [Claude pricing](https://claude.com/pricing) · [Anthropic on shared usage limits](https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work)

We *can* compare published **marginal token prices**, with the important qualification that API prices are **not subscription allowances**. For the same illustrative workload of **1 million input tokens and 200,000 output tokens**:

| Model | Input, per 1M tokens | Output, per 1M tokens | Cost of example workload |
| --- | ---: | ---: | ---: |
| SWE-2 | $3 | $15 | **$6** |
| Claude Fable 5.1 | $10 | $50 | **$20** |
| Claude Opus 5.5 | $4 | $20 | **$8** |
| Claude Sonnet 5 | $2 | $10 | **$4** |

SWE-2 buys more raw tokens per marginal dollar than Fable and Opus on this mix, while Sonnet costs less per token than SWE-2. SWE-2's listed rates apply after its temporary free period. Cache hits, model choice, output length, and orchestration change the actual bill. These are **model usage prices**, not what either $20 subscription promises to include. [Devin model prices](https://docs.devin.ai/desktop/models) · [Anthropic API prices](https://platform.claude.com/docs/en/about-claude/pricing)

The more compelling evidence for this article is Cognition’s published *task-level* result. On FrontierCode 1.1 Main, Cognition reports **SWE-2 at 50.0%**, near **Fable 5.1 at 50.9%**, for **64% lower average rollout cost** in its evaluated setups. It publishes **$3.28 per task for Fable 5.1 Medium**. Applying the 64% reduction implies **about $1.18 per SWE-2 rollout**; that latter number is arithmetic from Cognition’s claims, not a separately stated price. That is roughly **2.8 attempts at SWE-2’s measured average cost for the price of one Fable attempt**, assuming the same benchmark conditions. It does *not* mean 2.8 times as many included Devin Pro tasks as Claude Pro tasks. On another benchmark in Cognition’s own table, Terminal-Bench 4, SWE-2 scores **27.3%** versus **55.8%** for Fable 5.1; price alone does not settle which model is better for a given task. [Cognition: SWE-2](https://cognition.com/blog/swe-2)

![Cognition FrontierCode 1.1 Main chart: SWE-2 approaches Fable 5.1 score at lower average rollout cost](/images/swe-2-frontiercode-cost.png)

*Source: [Cognition, “Introducing SWE-2: Pushing the Pareto Frontier”](https://cognition.com/blog/swe-2). The chart compares a weighted benchmark score against mean USD cost **per rollout**, not subscription quotas or guaranteed cost per accepted PR. Image reproduced from Cognition’s post.*

Cognition’s [Fusion evaluation](https://cognition.com/blog/local-fusion) provides another system-level result: across several coding benchmarks, a frontier lead paired with SWE-2 as a sidekick reduced measured cost while keeping performance close to the frontier model alone. Those are results for particular model pairings and harness settings. For KEEP Terminal, the practical metric is **cost per accepted PR, including my review and rework**.

## The model under Devin: Kimi K3 to SWE-2

I’ve found SWE-2 equally capable at bounded, task-level iterations, especially when I give it detailed analysis, a plan, and context first. That planning can call for a model with a larger context window or stronger reasoning. Cognition’s Fusion workflow makes a similar division of work between agents; I’ll return to the harness below.

Devin is a platform, not a single model. In Devin CLI you can select among Cognition, Anthropic, OpenAI, and Google models, as well as supported open-weight families including **DeepSeek, Kimi, and GLM**; Devin Desktop also offers a model picker. Model availability varies by product, plan, and organization settings, so “plug in any model” would overstate the documentation. **SWE-2**, Cognition’s latest software engineering model, is specifically **post-trained from Kimi K3**. Selecting DeepSeek for a session would run a DeepSeek model in the Devin agent, not turn it into SWE-2 or mean Cognition has RL-trained that DeepSeek checkpoint. [Devin CLI models](https://docs.devin.ai/cli/models) · [Devin Desktop models](https://docs.devin.ai/desktop/models) · [Cognition: Introducing SWE-2](https://cognition.com/blog/swe-2)

### Brief background on Moonshot’s models

Moonshot AI, a Beijing-based company with investors including Alibaba and Tencent, built and released Kimi K3’s weights. It is a **2.8-trillion-parameter mixture-of-experts** model, with about **104 billion parameters activated per token**. Those figures describe total model capacity and the computation selected for a token, respectively; they are not interchangeable. Moonshot’s [technical report](https://arxiv.org/abs/2607.24653) documents its design and its own extensive RL across coding, agentic work, and general tasks. [Reuters: Moonshot and its investors](https://www.reuters.com/world/asia-pacific/chinese-ai-firm-moonshot-files-confidentially-hong-kong-ipo-sources-say-2026-09-03/)

What might it cost to build a model like this? Moonshot has not published K3’s training bill, but a comparison gives a sense of scale. DeepSeek reported **2.664 million H800 GPU-hours** to pre-train its 37-billion-active-parameter V3 model on **14.8 trillion tokens**, valuing that compute at **$2 per GPU-hour**. If I mechanically scale DeepSeek’s GPU-hours to K3’s **104 billion active parameters**, using K2’s published **15.5-trillion-token** budget as a stand-in, I get about **7.8 million H800-equivalent GPU-hours**. At DeepSeek’s assumed $2 per GPU-hour, that works out to roughly **$16 million in accelerator-rental-equivalent pre-training compute**. This is a back-of-the-envelope comparison, not Moonshot’s actual cost. K3’s architecture, routing, communication, long-context and vision training, GPU utilization, and hardware prices can all change the compute bill. Its RL, experiments, staffing, and release add further costs. Moonshot has not disclosed enough to estimate what building and releasing K3 cost overall. [DeepSeek-V3 technical report](https://arxiv.org/abs/2412.19437) · [Kimi K2 technical report](https://arxiv.org/abs/2507.20534) · [Kimi K3 technical report](https://arxiv.org/abs/2607.24653)

The point is that Cognition begins with a remarkably capable general model. Its contribution is to further train that starting model on the behaviors it wants in software engineering, and to deploy the result within Devin. **SWE-2 is a new model checkpoint derived from Kimi K3, not K3 with a different prompt.**

## What “model architecture” actually means

An analogy that helps me: **architecture is the wiring diagram and processing rules; weights are the learned numerical settings inside that wiring**. Kimi K3’s architecture includes “93 processing layers,” attention mechanisms for using earlier context, a vision encoder for images, and *mixture-of-experts* blocks. In each expert layer, a learned *router* scores a token’s internal representation and selects 16 of 896 routed expert networks to process it, alongside shared components. An “expert” is a neural network component, not necessarily a neatly labeled “Java expert” or “testing expert.” The router makes choices for tokens as they pass through these layers; it does not send an entire request to one preassigned expert. [Moonshot: Kimi K3 model description](https://github.com/MoonshotAI/Kimi-K3) · [Kimi K3 technical report](https://arxiv.org/abs/2607.24653)

K3 contains **2.8 trillion parameters in total**, while roughly **104 billion are activated to process a token**, about **3.7%** of the total. That active count includes more than the selected routed experts: shared and other model components also participate. The selected experts can differ from token to token; the diagram shows scale, not fixed compartments inside the model. [Moonshot: Kimi K3 model summary](https://github.com/MoonshotAI/Kimi-K3)

![Schematic of Kimi K3's 2.8 trillion total parameters and approximately 104 billion active per token](/images/kimi-k3-parameter-activation.svg)

*Diagram based on [Moonshot AI’s Kimi K3 model summary](https://github.com/MoonshotAI/Kimi-K3). Proportions are approximate; the router selects experts at each MoE layer.*

That wiring does not by itself make a useful programmer. Training sets the numbers that govern how the parts transform information—including how the router scores and combines experts. Cognition starts from Moonshot’s trained K3 weights and further updates the model. Its public SWE-2 post does not enumerate precisely which parameters changed in each step. The **104 billion active** number is per token; different tokens can activate different experts across a training run.

It is also worth resisting an unsupported comparison: OpenAI has disclosed a mixture-of-experts design for its **gpt-oss** models, but I have not found a corresponding public disclosure confirming whether **GPT-6 Astra** or the current **Claude Opus** models use MoE. [OpenAI: Introducing gpt-oss](https://openai.com/index/introducing-gpt-oss/)

## How do you train trillions of parameters from a coding task?

This is the part of the process I still want to understand better. A few coding tasks cannot teach the model everything; each attempt provides a piece of feedback. For each generated token, only part of K3’s model is active; across a longer attempt, different tokens can use different experts. Training combines signals from many attempts across many tasks, makes small weight updates, and repeats. The **2.8 trillion** figure describes the model’s total size, not a set of values that a single coding task somehow determines.

The way I can wrap my head around it: imagine several agent attempts at the same repository task. Some produce working code and pass a trustworthy verifier; others fail, take costly detours, or exploit a weakness in the test. The agent records the sequence of model outputs and tool interactions, its *trajectory*. Cognition evaluates success and cost, then uses those outcomes as a learning signal. Its SWE-2 post expresses the reward at an effort level as approximately:

\[
R = S - \lambda_e C
\]

Here, **S** is whether the attempt succeeded, **C** combines inference expense and rollout time, and **λₑ** sets the cost penalty for that reasoning-effort level. Success matters, but so does avoiding unnecessary expense. Cognition says it trains multiple effort levels in one RL run. [Cognition: SWE-2 training objective](https://cognition.com/blog/swe-2)

The reward does not arrive with a note saying “change parameter 846,271.” As the agent works, the model assigns *probabilities* to possible next outputs and generates one sequence of choices. The math traces those choices through the weights that helped produce them. It then uses the attempt’s score to estimate small changes that would make better-than-baseline sequences more likely and worse-than-baseline ones less likely. [Cognition: SWE-2 reward baseline](https://cognition.com/blog/swe-2)

**RL training gradually tilts the odds.** An individual attempt can get lucky or take a poor path; its signal is noisy. Across many tasks and attempts, the updates can favor patterns that work more often while discouraging patterns that fail or waste effort. That does not guarantee an improvement on every task. Cognition evaluates the resulting model and says it strengthened its verifiers when more capable models revealed grading errors or ways to exploit them. [Cognition: SWE-2 data improvements](https://cognition.com/blog/swe-2)

For readers curious about the math, the following simplified policy-gradient estimator is **from Cognition’s SWE-2 post**:

\[
\hat g = \frac{1}{n}\sum_{i=1}^{n}(R_i-b)\nabla_{\theta}\log \pi_{\theta}(y_i\mid x)
\]

In plain English, the first part compares an attempt’s reward with a baseline; the second estimates how a change in weights would affect the likelihood of the generated sequence. Cognition says its actual training uses *off-policy* RL and a length-weighted baseline, so this equation illustrates the central idea rather than describing its complete implementation. [Cognition: SWE-2 reward baseline and rollouts](https://cognition.com/blog/swe-2)

The model then tries more tasks using updated weights, and the cycle repeats. In its earlier SWE-1.7 description, Cognition explains how a trainer distributes updated weight *deltas* to the machines generating the next attempts. [Cognition: SWE-1.7 training infrastructure](https://cognition.com/blog/swe-1-7)

The TL;DR based on Cognition’s account: **it updates the model’s weights by practicing on many software engineering tasks, then releases the trained SWE-2 model when the improvements are ready**. So an already capable general model can become better suited to the coding work Cognition wants it to do. Cognition also keeps improving the training environments and verifiers that produce the learning signal. The agent harness is another part of the picture: it shapes what the trained model can do when someone puts it to work. [Cognition: SWE-2](https://cognition.com/blog/swe-2)

## The harness: where trained capability becomes a working agent

A model alone generates outputs. An **agent harness** supplies the working loop around it: repository access, tool calls, shell commands, context management, feedback from tests, and rules for when to ask, continue, or stop. Claude Code has an agent harness of its own. Devin has its own runtime and team workflow. A model’s performance in a coding benchmark reflects both its learned behavior **and** the environment in which it acts. Cognition’s evaluation methodology even reports some models under their primary, different harnesses, which limits any claim that benchmark gaps are entirely due to weights. [Cognition: SWE-2 evaluation methodology](https://cognition.com/blog/swe-2) · [Anthropic: Claude Code overview](https://code.claude.com/docs/en/overview)

Cognition’s **Fusion** is a particularly clear example of harness design. It keeps two agents with separate contexts: a frontier **lead** interprets the task, plans, and reviews; a less expensive **sidekick**, often SWE-2, explores, implements, and tests delegated work. The lead can correct the sidekick or take control. That is a runtime arrangement, **not** the RL algorithm that produced SWE-2’s weights. Cognition tunes the instructions and delegation boundary for different model pairs. [Cognition: Introducing Fusion](https://cognition.com/blog/local-fusion)

![Flow from Moonshot Kimi K3 through Cognition RL training to SWE-2, the Devin agent harness, and a reviewable pull request](/images/devin-rl-harness-flow.svg)

The diagram shows two improvement cycles that can reinforce each other. Better training environments and rewards can produce a better **future model checkpoint**. Better runtime tools and orchestration can improve an agent’s work **without changing weights**. Training in an environment close to production can help the model learn behavior useful in that environment; Cognition says it trained SWE-1.7 directly in the Devin harness. [Cognition: SWE-1.7](https://cognition.com/blog/swe-1-7)

## The bigger question

What interests me most is the pattern beyond Devin. This example shows how it works: Moonshot invests in a broadly capable model. Cognition starts from that model, applies verifiable software-engineering RL, and builds a runtime that can put the resulting capability to work in a real repository. The model, the training tasks, the verifier, the harness, and the human review process each contribute to the result.

This suggests an analogous path for companies that do not build a frontier foundation model from scratch: begin with strong open weights, measure a specific class of work, train against outcomes that matter, and keep improving the environment in which the model operates. The hard part is defining *success* well enough that the system moves toward more useful outputs in a given domain instead of merely learning to pass a test. If that can be done reliably, specialized agents may improve through a tight loop between real tasks, verifiable feedback, model updates, and better tools.

Software engineering offers an unusually concrete place to see that loop in action, but there are other domains with clear, checkable outcomes where it could apply. The future is bright.
