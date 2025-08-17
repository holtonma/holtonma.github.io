# Hugo Blog Todo List

## Project Overview

**Site**: holtonma.github.io  
**Framework**: Hugo (Static Site Generator)  
**Theme**: [PaperMod](https://github.com/adityatelange/hugo-PaperMod)  
**Hosting**: GitHub Pages with GitHub Actions  
**Deployment**: Automatic on push to `main` branch  

### Tech Stack
- **Hugo** v0.147.9+ (extended version)
- **PaperMod Theme** - Clean, fast, responsive blog theme
- **GitHub Actions** - CI/CD for automatic deployment
- **Git Submodules** - Theme management
- **Markdown** - Content authoring

### Key Features Enabled
- Dark/Light mode toggle
- Search functionality
- Social media integration
- Twitter Cards & Open Graph
- Custom share buttons
- Professional navigation
- Responsive design

## Post-Launch Tasks

### Analytics & SEO
- [x] Set up Google Analytics
  - [x] Create Google Analytics property for holtonma.github.io
  - [x] Get Measurement ID (G-3VHWR9KEC4)
  - [x] Configure GA4 tracking in hugo.toml
  - [ ] Optional: Set up Google Search Console and replace `YOUR_SEARCH_CONSOLE_TAG`

### Content & Features
- [ ] Complete reranker blog post with real suggest.watch examples (target: Aug 19, 2025)
  - [x] Add TLDR/Key Takeaways section for immediate digestibility
  - [ ] Create visual decision framework table/graphic for when to use vs skip rerankers
  - [ ] Add time-sensitive disclaimer to clarify evergreen vs current vendor info
  - [ ] Improve narrative flow with better subheaders for easier scanning
  - [ ] Add 1-2 external benchmark references (MS MARCO, HuggingFace) for credibility
  - [ ] Strengthen conclusion by bringing suggest.watch personal narrative full circle
- [ ] Consider adding more blog posts about:
  - [ ] Data platform architecture patterns
  - [ ] Agent-driven system design
  - [ ] Career transition insights
- [ ] Add RSS feed promotion
- [ ] Consider adding newsletter signup
- [ ] Add commenting system (if desired)

### Home Lab Infrastructure Tasks
- [ ] Set up Nginx container on Proxmox for ASRock home lab
- [ ] Hook up PydanticAI web app to local models on ASRock
- [ ] Move Cloudflare tunnel to container on ASRock and test with eyeonmajors
- [ ] Build real-world examples for reranker post using suggest.watch data

### Technical Enhancements
- [ ] Test Twitter Card display with Twitter Card Validator
- [ ] Verify Open Graph tags for LinkedIn sharing
- [ ] Consider adding search functionality enhancements
- [ ] Add structured data markup for SEO

### Performance & Monitoring
- [ ] Set up website monitoring/uptime checks
- [ ] Analyze Core Web Vitals
- [ ] Review and optimize image loading

## Deployment Issues Resolved ✅

### GitHub Pages Jekyll vs Hugo Conflict
**Issue**: GitHub Pages was intermittently running Jekyll instead of Hugo, causing posts to disappear randomly.

**Root Cause**: GitHub Pages defaults to Jekyll for any repository with markdown files. Even with custom Hugo workflows, it would sometimes override with automatic Jekyll builds.

**Solution**: 
1. Created `.github/workflows/blog_publish.yml` with proper Hugo workflow
2. Ensured GitHub Pages source is set to "GitHub Actions" in repository settings
3. Added `static/.nojekyll` file to disable Jekyll processing
4. Used `--cleanDestinationDir` flag in Hugo build for consistent deploys

**Key Files**:
- `.github/workflows/blog_publish.yml` - Custom Hugo deployment workflow
- `static/.nojekyll` - Disables Jekyll processing
- `.gitignore` - Excludes `public/` directory from version control

**Verification**: GitHub Pages UI should show "Deploy Hugo site to Pages workflow" as the source.

## Content Quality Framework

### Technical Content Standards
See `content-guidelines.md` for detailed guidance on creating credible, long-lasting, shareable technical content.

**Key principle**: Review all blog posts against the three pillars (Credibility, Long-Lasting, Shareable) before publishing.

**Quick reference checklist:**
- [ ] Credible: Evidence-based claims, transparent tradeoffs, clear definitions, concrete examples
- [ ] Long-lasting: Focus on concepts over vendor features, timeless analogies, decision frameworks
- [ ] Shareable: Compelling hooks, visual elements, actionable insights, fair but opinionated takes

## Completed ✅
- [x] Hugo site setup with PaperMod theme
- [x] About page with Publications and Patents
- [x] Four blog posts with hero images and AI-generated artwork
- [x] Twitter Card meta tags configured
- [x] GitHub Actions deployment workflow (Hugo, not Jekyll!)
- [x] Custom share buttons (removed Facebook/WhatsApp)
- [x] Professional navigation menu
- [x] Social media links with custom SVG icons
- [x] Resolved GitHub Pages Jekyll/Hugo deployment conflicts
- [x] Google Analytics 4 tracking implemented
- [x] Google Search Console verification configured
- [x] SEO optimizations (robots.txt, alt text, structured data)
- [x] Automatic pagination setup (10 posts per page default)
- [x] Technical content framework added to CLAUDE.md for guidance