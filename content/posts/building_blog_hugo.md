---
title: "Building This Blog: Why Hugo + GitHub Pages + Leonardo.ai"
date: 2025-07-06T10:00:00-05:00
draft: false
tags: ["Hugo", "Go", "GitHub Pages", "Blogging", "Leonardo.ai", "Static Sites"]
categories: ["meta", "technical-setup"]
description: "Why I chose Hugo and GitHub Pages for this blog, how it connects to my appreciation of Go, and my workflow for creating content with AI-generated imagery."
author: "Mark Holton"
cover:
    image: "/images/hugo_blog_building.jpg"
    alt: "Whimsical cartoon illustration of a determined Gopher mascot sitting at a computer building a Hugo blog with floating markdown files and GitHub icons"
    caption: "Crafting the perfect blogging workflow"
---

![Whimsical cartoon illustration of a determined Gopher mascot sitting at a computer building a Hugo blog with floating markdown files and GitHub icons](/images/hugo_blog_building.jpg)

*[Generated with [Leonardo.ai](https://leonardo.ai/) using prompt: "A whimsical cartoon illustration in classic cartoon style showing a determined Gopher sitting in a cozy computer chair ..."]*

## Why I Built This Blog

After years of keeping technical notes scattered across various platforms, I wanted a single place to document my journey as a software architect, share what I'm learning about data pipelines and recently about AI integration, and connect with others navigating similar technical challenges.

But I had specific requirements that ruled out the usual suspects (Medium, Dev.to, etc.):

- **Technical flexibility** to customize and evolve
- **Low friction** for daily writing and publishing
- **Ownership** of my content and presentation
- **Professional credibility** with a clean, fast experience
- **No vendor lock-in** or algorithm dependency

Enter Hugo + GitHub Pages + Leonardo.ai.

## Why Hugo? 

After spending the last few years deep in Java, Kafka, and lately some Python and various data pipeline technologies, I found myself craving the simplicity and elegance of Go. Go is my tool when I need concurrency and performance, and while generating blog pages doesn't require much of that and while Hugo doesn't require writing Go code, it gave me an excuse to be around the Go ecosystem again.

But beyond nostalgia, Hugo solved real problems:

### Speed and Simplicity
Hugo builds are **fast**. My entire site regenerates in under 100ms locally. Coming from Jekyll experiences where builds took 30+ seconds, this feels magical.

### Markdown-First Philosophy
Hugo embraces markdown as the primary content format, which aligns with how I already take notes and document code. No fighting with WYSIWYG editors or complex content management interfaces.

### Single Binary
No Ruby gems, Python virtual environments, or Node.js dependency hell. Hugo is a single binary that just works. Download, run, done.

### Themes and Extensibility
The theme ecosystem is mature, and customization is straightforward. I started with PaperMod (a clean, technical theme) and can evolve the design as needed.

## Why GitHub Pages?

Free hosting that deploys automatically from my repository.

But GitHub Pages offers more than a few bucks savings:

### Version Control for Everything
My entire blog lives in Git - content, configuration, themes, images. I can track changes, roll back, branch for experiments, and never lose work.

### GitHub Actions Integration
Every `git push` triggers an automated build and deployment. No manual steps, no separate hosting concerns. The workflow is:

```bash
# Write post
hugo new posts/my-topic.md
# Edit in any markdown editor
# Preview locally
hugo server -D
# Publish
git add . && git commit -m "New post" && git push
```

Within 30 seconds, the post is live.

### Professional Domain Options
While I'm using the default `holtonma.github.io` for now, GitHub Pages supports custom domains. I can add a custom domain later without changing anything else.

### Reliability
GitHub's infrastructure handles traffic spikes, global CDN distribution, and uptime monitoring. I focus on content, not server management.

## The Creative Element: Leonardo.ai for Imagery

![Artistic illustration of a Go gopher mascot painting or creating digital artwork, representing the creative process of generating AI imagery for blog posts](/images/gopher_painting.jpg)

Technical blogs can feel sterile. I wanted to add visual interest without stock photo or copyright concerns.  I can be creative in the images I want to highlight the writing. I generate custom images that match the exact content and mood of each post. The MCP integration post got retro-futuristic data pipeline imagery. This post is a gopher blogging.

**Leonardo.ai solved this beautifully.**

### Creative Prompting Practice
Crafting AI image prompts is surprisingly similar to architecting software systems - you need to be specific about requirements, consider edge cases, and iterate toward the desired outcome.

### Example prompt workflow:
```
Initial: "Software engineer building a blog"
Refined: "Whimsical illustration of a software engineer in a modern workspace, surrounded by floating markdown files and code symbols, warm lighting, technical but friendly atmosphere"
Final: "A whimsical cartoon illustration in classic cartoon style showing a determined Gopher sitting in a cozy computer chair …"
```

### Cost-Effective and Flexible
Leonardo.ai's credit system is far more economical than commissioning custom illustrations, and I can iterate quickly until the image captures exactly what I want.

## The Technical Workflow

My blogging workflow is intentionally lightweight:

### Writing
```bash
# Start new post
hugo new posts/topic-name.md

# Edit in any markdown editor (I use VS Code)
# Front matter is auto-generated with proper dates, tags, etc.
```

### Local Preview
```bash
# Real-time preview with hot reloading
hugo server -D

# Available at localhost:1313
# Changes appear instantly as I write
```

### Publishing
```bash
# When ready to publish
git add .
git commit -m "Add post: [topic]"
git push

# GitHub Actions handles the rest
# Live in ~30 seconds
```

### Image Creation
1. Write the post content first
2. Identify key concepts or mood for imagery
3. Craft Leonardo.ai prompt based on post themes
4. Generate 3-4 options, pick the best
5. Download and add to `/static/images/`
6. Reference in post front matter

## What This Setup Enables

This technical foundation serves my broader goals:

### **Low Friction Documentation**
When I solve an interesting technical problem or discover a useful pattern, I can have it documented and published in under 30 minutes. The barrier between "had an insight" and "shared with the world" is minimal.

### **Learning in Public**
By committing to regular posts about what I'm building and learning, I'm forced to articulate my thinking clearly. This deepens my own understanding while potentially helping others.

### **Professional Platform Building**
Eventually, as I transition toward more advisory work, it is a piece of demonstrating both technical depth and communication skills. It's a living portfolio of how I think about complex problems.

### **Multi-Audience Content Strategy**
I plan to write for different audiences with clear tagging:

- **Technical deep-dives** (tagged `technical-deep-dive`) for fellow engineers who want implementation details, code examples, and architectural decisions
- **Concept-level posts** (tagged `business-concepts`) for business stakeholders, product managers, and anyone interested in the strategic implications of technical choices

The goal is sharing ideas that share thinking beyond the engineering domain - helping bridge the gap between technical possibility and business value.

### **Community Connection**
Technical blogging opens conversations with peers facing similar challenges, and always interested in connecting with others working on similar goals and challenges.  Reach out!

## Lessons Reinforced

### **Start Simple, Evolve Gradually**
Started with basic Hugo + PaperMod theme + GitHub Pages. No custom domains, complex analytics, or advanced features. Ship first, optimize later.

### **AI Tools Are Collaboration Partners**
Leonardo.ai doesn't replace creativity - it is a partner that allows me to amplify the ideas. The best results come from clear vision and iterative refinement, just like software design.

### **Version Control**
The blog lives in the same familiiar environment we are working in every day - Git.  Want to try a new theme? Create a branch. Not working? Revert. This freedom accelerates iteration.


## This blog

Hugo + GitHub Pages + Leonardo.ai - flexible and cost-effective platform for technical content creation. Most importantly to me, it gets out of my way and lets me focus on sharing the ideas.

If you're considering starting a technical blog, this stack is worth exploring. 

---

**Tech Stack**: [Hugo](https://gohugo.io/) 0.147.9, [PaperMod theme](https://github.com/adityatelange/hugo-PaperMod), [GitHub Pages](https://pages.github.com/), [GitHub Actions](https://github.com/features/actions), [Leonardo.ai](https://leonardo.ai/)  
**Writing Time**: ~45 minutes from idea to published post  
**Deployment Time**: ~30 seconds from `git push` to live site
