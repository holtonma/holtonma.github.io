# Technical Content Guidelines

**Goal**: Create credible, long-lasting, shareable technical content that builds authority and drives engagement.

## Before You Start

### Define Your Audience
Always define your intended reader up front—their technical level, goals, and context. This affects technical depth, jargon usage, and example selection.

**Target reader profiles:**
- **Beginners**: New to the technology, need foundational concepts and clear definitions
- **Practitioners**: Working professionals, want implementation details and real-world examples
- **Decision-makers**: Managers/architects, focus on business impact and strategic considerations
- **Experts**: Advanced users, interested in edge cases, performance optimizations, and novel approaches

### Accessibility and Inclusivity
- **Use plain language**: Favor simple, direct language over jargon when possible
- **Define acronyms and technical terms**: Don't assume prior knowledge
- **Keep paragraphs short**: Break up dense content for easier reading
- **Consider non-native speakers**: Use clear sentence structure and common vocabulary
- **Avoid exclusionary language**: Use inclusive examples and avoid assumptions about background
- **Add alt text to images**: Ensure visual content is accessible to screen readers

## The Three Pillars

### ✅ Credibility (Technical Authority)

- **Ground claims in evidence** – cite benchmarks, research papers, official docs, or production case studies
- **Transparency about tradeoffs** – mention not just advantages, but limitations (speed vs cost vs accuracy, etc.)
- **Clarity of definitions** – don't assume readers know technical terms; define and contrast with alternatives
- **Concrete examples** – showing real use cases (like `suggest.watch`) builds trust and demonstrates practical application
- **Code snippets & reproducibility** – show readers how they could try it themselves with working examples
- **Performance metrics** – include actual numbers, testing methodology, and measurement conditions

### ✅ Long-Lasting (Evergreen Value)

- **Explain underlying concepts, not just vendor features** – e.g., the architecture of rerankers won't change quickly, even if specific APIs do
- **Use timeless analogies** – comparing rerankers to "critics versus creators" is sticky and will still make sense later
- **Avoid hype-driven language** – skip words too tied to a specific moment ("revolutionary," "hot new model") unless qualified
- **Offer decision-making frameworks** – when to use vs skip approaches, cost vs accuracy tradeoffs last longer than vendor-specific details
- **Separate principles from implementations** – focus on patterns that transcend current tools

### ✅ Shareable (Maximum Impact)

- **Narrative hooks** – start with real pain points ("Blade Runner but less depressing") and compelling user stories that are memorable
- **Digestible storytelling** – combine case studies + diagrams + analogies. People share content that teaches and entertains
- **Visual elements** – diagrams, simple examples, screenshots spread easier than raw text
- **Actionable TLDR** – readers love sharing posts they can summarize as "it's basically X vs Y, here's when to pick one"
- **Opinionated but fair** – being pragmatic ("Voyage is best balance; Cohere when accuracy matters") makes content worth recommending
- **Quotable insights** – create memorable one-liners that capture key principles

## Content Review Process

**Before publishing any blog post, review against this checklist:**

### Credibility Check
- [ ] Have I cited authoritative sources and included real examples?
- [ ] Did I include metrics and can readers reproduce results?
- [ ] Am I transparent about limitations and tradeoffs?
- [ ] Are technical concepts clearly defined with concrete examples?
- [ ] Do I show implementation details and production considerations?

### Longevity Check
- [ ] Will this be useful in 2-3 years?
- [ ] Have I separated principles from vendor specifics?
- [ ] Did I provide reusable decision-making frameworks?
- [ ] Are my analogies and examples timeless?
- [ ] Do I focus on underlying concepts vs temporary features?

### Shareability Check
- [ ] Is there a compelling narrative hook and clear value proposition?
- [ ] Can someone easily summarize this to a colleague?
- [ ] Did I include visual elements and quotable insights?
- [ ] Are there clear, actionable takeaways?
- [ ] Is the content opinionated but fair in its recommendations?

## Preferred Content Structure

1. **Opening Hook** – Real problem or compelling use case that draws readers in
2. **Technical Deep Dive** – Core concepts, architecture decisions, implementation details
3. **Practical Application** – Real examples, cost/benefit analysis, decision frameworks
4. **Future Considerations** – Emerging trends, evolution of the problem space, next steps
5. **Actionable Summary** – Key takeaways, decision criteria, resources for further learning

## Content Types That Work Well

### Technical Deep Dives
- Architecture patterns and design decisions
- Performance comparisons with real benchmarks
- Implementation guides with reproducible examples
- Technology evaluation frameworks

### Case Studies
- Real production implementations
- Problem → solution → results narratives
- Cost/benefit analysis with actual numbers
- Lessons learned and pitfalls avoided

### Decision Frameworks
- When to use vs avoid certain approaches
- Technology selection criteria
- Tradeoff analysis templates
- Evaluation checklists

## Quality Indicators

**Great technical content:**
- Becomes a reference that people bookmark and return to
- Gets shared with colleagues as "you should read this"
- Helps readers make better decisions in their own contexts
- Combines technical depth with clear storytelling
- Provides practical frameworks beyond just explanation

**Avoid:**
- Pure vendor pitches without balanced analysis
- Hype-driven language without substance
- Complex topics without clear definitions
- Claims without evidence or reproducible examples
- Generic advice that could apply to any technology

## Writing and Review Process

### Draft Review and Feedback
- **Get SME review**: Have at least one subject matter expert review for technical accuracy
- **Test with target audience**: Share drafts with intended readers to validate clarity and usefulness
- **Check assumptions**: Verify that examples and analogies resonate with your audience

### Multi-Pass Revision
Approach editing in separate focused passes:
1. **Content pass**: Structure, completeness, technical accuracy
2. **Clarity pass**: Flow, transitions, definitions, accessibility
3. **Style pass**: Grammar, tone, formatting consistency

### Style and Consistency
- Follow established style guide for grammar, tone, and formatting consistency
- Maintain consistent terminology throughout the piece
- Use consistent code formatting and naming conventions
- Ensure consistent voice and perspective

## Content Maintenance

### Keeping Content Fresh
- **Schedule periodic reviews**: Technical content should be reviewed quarterly or bi-annually
- **Update time-sensitive information**: Refresh benchmarks, version numbers, and API references
- **Monitor feedback**: Track comments and questions to identify areas needing clarification
- **Archive outdated content**: Remove or clearly mark content that's no longer relevant

## Meta-Goal: Connection to Real Work

**The best technical posts don't just explain how something works—they help readers make better decisions in their own contexts.**

Great technical content bridges abstract concepts and practical application. Readers should finish your post thinking, "I know exactly when and how to apply this in my work," not just "that was interesting."

**Indicators of work-connected content:**
- Readers can assess if the solution fits their use case
- Decision frameworks help evaluate tradeoffs in context
- Real examples show production relevance
- Cost/performance data supports stakeholder conversations
- Implementation details turn "understanding" into "doing"

**The test**: Would a practitioner bookmark this as a reference for a similar challenge? If not, add more practical context, decision criteria, or real-world constraints.

When you combine technical depth with clear storytelling and actionable frameworks, you create content that builds authority and genuine value for the community. The best posts become references—bookmarked, shared, and revisited when facing real-world problems.