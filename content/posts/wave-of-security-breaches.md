---
title: "A Week of Cyberattacks and a Call Back to the Fundamentals"
description: "After a week that brought a fully automated AI cyberattack and malicious code on 178 major websites through one vendor's scripts, here's how I'd raise the security bar: strong basics on your own accounts, AI on defense, and security built into design, review, deployment and operation."
tags: ["security", "AI", "threat-model", "appsec", "supply-chain"]
categories: ["ai-engineering"]
ShowToc: true
TocOpen: false
date: 2026-11-22T13:34:11-05:00
author: "Mark Holton"
draft: false
cover:
    image: "/images/wave-of-security-breaches-hero.jpg"
    alt: "Illustration of a legion of dark, red-eyed robots advancing toward a cracked fortress defended by white robots, with bank-like symbols connected by red lines between them."
    caption: "As automated attacks become cheaper and more capable, defenders need both AI assistance and stronger foundations: secure design, testing, patching, and recovery."
factoryh_piece: "adcb5a95-8a23-4903-8637-f091e538e348"
---

While I've always thought security was important, attackers' capabilities keep evolving, and that calls for a new level of attention. The recent wave of breaches, and how varied and sophisticated they've become, is a bit of an alert.

![Illustration of a legion of dark, red-eyed robots advancing toward a cracked fortress defended by white robots, with bank-like symbols connected by red lines between them.](/images/wave-of-security-breaches-hero.jpg)
*As automated attacks become cheaper and more capable, defenders need both AI assistance and stronger foundations: secure design, testing, patching, and recovery.*

On 17 November, two stories came through my feed:

- **Autonomous AI exploitation.** [@unusual_whales](https://x.com/unusual_whales/status/2122506553047814275) posted that Google says "the era of autonomous attacks has arrived": AI reading software updates, working out which flaw each patch fixes, and building an exploit before companies can install the fix, with no human involved. POLITICO covers the Google report itself: [Google says Russian speakers pulled off first-ever fully automated AI cyberattack](https://www.politico.eu/article/google-says-russian-speakers-behind-first-ever-fully-automated-ai-cyberattack/).
- **178 major websites, one vendor.** [Newsweek reports](https://www.newsweek.com/cyber-attack-websites-affected-12725863) that "hackers have planted malicious code on some of the world's most popular websites, potentially exposing visitors to the theft of their personal and financial information." The security firm Report URI identified 178 affected organizations, and Newsweek publishes the full list: Zoom, Salesforce, GitLab, CNN, BBC, HSBC, Equifax, IKEA, Air France-KLM, Starbucks Canada, UNICEF USA and many more. According to the researchers Newsweek quotes, the hackers "injected malicious JavaScript" into scripts hosted by Optimizely, a company whose software lets businesses test different versions of their websites. Newsweek also describes the code as aimed at payment-card theft and at attacks on older iPhones and iPads. Optimizely confirmed the incident to Newsweek: "On November 16, 2026, Optimizely identified a security incident in which an unauthorized party exploited a vulnerability in the Optimizely Experimentation to add malicious JavaScript to some customer projects." I first saw it in a post by [@HormuzLetter](https://x.com/HormuzLetter/status/2122535982591365248).

The aggregator accounts are where I saw the news, not the reporting itself, so I've linked the original coverage for each item. Newsweek notes that some names on its list are individual websites or regional services rather than whole companies: HSBC, for example, shows up a dozen times, once per country site.

Two different kinds of event in one week: automated exploitation, and malicious code on 178 organizations' sites at once. The bar has gone up for everyone, not just for the obvious targets.

This post isn't a case for a fresh start. It's about what changed on the other side of the table, that attacks cost less to build than they used to and can do more, and what I'd do about it. Using the same AI leverage on defense is part of the answer. It isn't the whole answer.

## The sharpest example: what Google reported

The Google item is the one I'd look at most closely, so here's what the [POLITICO article](https://www.politico.eu/article/google-says-russian-speakers-behind-first-ever-fully-automated-ai-cyberattack/) says.

According to the article, Google's cyber threat intelligence division said it had spotted hackers using AI to:

> "fully automate vulnerability discovery and exploitation without a human in the loop for the first time."

The details, as POLITICO reports them:

- The hackers set up a series of AI agents to "continuously compare pre- and post-patch code, identify vulnerabilities, and automatically develop exploits without human intervention," Google said.
- Google identified them as Russian speakers from technical documentation written in Russian.
- They targeted French websites in media, entertainment and education.
- POLITICO calls it what "may be" the first fully automated attack. Until now, it says, even the most advanced models "often required skilled hackers to guide them or fix mistakes."

That's Google's claim as POLITICO reports it. I haven't verified it myself.

## My view: the economics moved

From here on it's my own inference, not something the reports prove.

The line I keep coming back to is the one about skilled hackers. Before, they had to guide the models and fix their mistakes. That skilled person was the expensive part of an attack. If agents can find a flaw and build the exploit on their own, the cost of probing one more app gets close to the cost of compute. And it isn't only cheaper: an attack that works without that person can do things it couldn't before.

So I expect the odds that any given app gets probed to go up, even if your code hasn't changed. Nothing about your app got worse. Looking at it just got cheaper.

The 178-site incident points at the same economics from another direction. Newsweek's list runs from banks and airlines to retailers, charities and a handful of universities. According to Newsweek, it all came through scripts hosted by one vendor, Optimizely. None of those organizations had to make a mistake in their own code for their visitors to be exposed. The attacker got in once and got reach across all of them.

How they got in fits the pattern too: brute force. Newsweek reports that, in a security report Optimizely published, the company said the attackers "made thousands of attempts to guess employee email addresses before gaining access to customer projects and inserting malicious code." Brute-forcing is patient, repetitive work, exactly the kind that gets cheaper when it's automated. Nothing I've read says AI was involved here, so I'm not claiming it was.

That puts pressure on a naive but sometimes common old assumption: "we're too small to be worth the effort." That reasoning relied on attacks being expensive and aimed one target at a time. If they're cheap, or if they arrive through something you share with bigger companies, the set of apps worth trying gets bigger.

This isn't only for those of us who build and host apps. All of us should treat it as a call back to the fundamentals on our own personal accounts: pick strong passwords, use a password manager such as [1Password](https://1password.com/), and always use 2FA (two-factor authentication).

## Use the same leverage

Attackers are using AI to move faster. The POLITICO article says as much: AI lets them "accelerate attacks and make them more targeted." As app creators and defenders of our users, we should use it too.

For indie devs, the easiest start is an AI-assisted review: if you use Claude Code, its `/security-review` command, or Anthropic's [Claude Security](https://claude.com/product/claude-security) product. You don't need a security program to take that first step, and it will give you "table stakes" for your changes. `/security-review` audits your local code changes (the branch diff) for common security vulnerabilities before you commit. What it checks for:

- **Injection flaws:** SQL injection, command injection, and unsanitized user input passed into execution sinks.
- **Cross-site scripting (XSS):** client-side script injection risks.
- **Authentication and authorization:** access control mistakes and auth flaws.
- **Data handling and exposure:** weak input validation and sanitization, sensitive data exposure, and cryptographic issues.
- **Configuration, business logic and dependencies:** configuration security, business logic flaws, code execution risks, and third-party package and supply-chain issues.

That's table stakes, not the finish line. For an application people depend on, a review command is one tool among several.

## Build security into how you ship

For an application people depend on, and in our "day job" for larger apps, I'd want security built into design, code review, deployment and operation.

If your team already takes security seriously, you already have the fundamentals: least privilege, reviewing dependencies, authentication that isn't an afterthought. Keep them. This isn't a list of things I've already put in place everywhere. It's where I'd start as a software engineer or architect.

**Start with the design.** Before reviewing individual lines of code, sketch where sensitive data goes, what is exposed to the internet, and which systems trust each other. What happens if someone takes over a user account? A vendor account? A deployment credential? A short threat-modeling session can expose assumptions that a code scanner never sees. OWASP provides a practical structure for that discussion in its [Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html).

**Put automated checks into the development workflow.** [Snyk](https://snyk.io/) offers scanning for application code, open-source dependencies, container images and infrastructure configuration. Those cover different sources of risk. I'd integrate the relevant checks into pull requests and the build pipeline, alongside secret scanning, so findings appear while someone is already working on the change. Give actionable findings an owner and a deadline; document exceptions and revisit them. A dashboard full of unassigned warnings doesn't fix an application.

**Make internal reviews specific.** "Please review this for security" is a broad request. Ask another engineer to examine particular failure cases: Can one customer access another customer's records? Can a regular user call an administrator's endpoint directly? What happens after a session is revoked? Reviewers need to understand the application's intended permissions, and those expectations should become automated tests. Once those permissions and failure cases are documented, they can also give AI-assisted reviews useful context: what the application should allow, what it must prevent, and which tests should verify those boundaries. OWASP's [Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/) gives teams a shared set of requirements to work from.

**Test the running application.** Reading source code and testing a deployed system answer different questions. Tools such as [ZAP](https://www.zaproxy.org/getting-started/) can help examine a running web application, but coverage matters, as it does with any automated review: authenticated areas need authentication configured, and automated exploration needs to be supplemented with realistic user flows. For higher-risk applications, I'd also budget for an independent penetration test, particularly before major releases involving sensitive data or new access boundaries.

**Patch quickly, and patch safely.** The agents Google describes worked by comparing code before and after a patch. My reading is that a published fix now works as a map to the flaw it fixes, and an automated one at that, so the gap between "a patch is out" and "an exploit exists for the unpatched version" probably shrinks. How long your apps run behind on patches matters more than it did. But speed has its own risk. The same week, [@KobeissiLetter](https://x.com/KobeissiLetter/status/2122715520281743849) posted about an outage at NSANet, the NSA's classified network. CNN reported, in coverage syndicated by Yahoo, that the almost four-day outage appeared connected to updates addressing PHP vulnerabilities: systems did not come back online as expected after patching. Officials said it was not a cyberattack, and mission-critical intelligence-gathering systems remained operational ([CNN](https://www.cnn.com/2026/11/20/politics/nsa-highly-classified-network-outage-resolved); [Yahoo](https://nz.news.yahoo.com/outage-nsa-highly-classified-communications-140904814.html)). The reported connection to patching illustrates why recovery planning matters alongside speed. Patching under pressure needs tested updates, staged deployments and recovery procedures you've practiced.

**Treat third-party browser code as part of your application.** The Optimizely incident makes this especially relevant. Know which scripts your pages load, who can change them, and how you would disable them quickly. Remove unnecessary scripts and keep them off sensitive pages where possible. Consider isolation, Content Security Policy and Subresource Integrity where appropriate. These controls have limits: allowing a vendor's domain does not establish that every script it serves is safe, and integrity hashes require managing changes to the expected file. OWASP's [Third Party JavaScript Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html) covers the options.

**Plan for the day something gets through.** My checklist would include restricted production access, narrowly scoped service credentials, useful security logs, and alerts someone owns. I'd also want a tested way to revoke credentials, disable a compromised integration, roll back a deployment and restore data. Finding a vulnerability is one responsibility. Containing an incident and recovering from it are responsibilities too.

**Pool what you learn, and make it repeatable.** Use AI to summarize advisories and write-ups for the stack you run, so you read what applies to you instead of everything. Then turn what you learn into a checklist or a recurring review, so it doesn't depend on someone remembering.

## What to do this week

- On your own accounts: strong passwords, a password manager, and 2FA everywhere.
- Sketch one app's data flows and trust boundaries, and ask what happens if a user, vendor or deployment account is taken over.
- Check how far behind on patches your apps and their dependencies are, and how you'd roll back a patch that breaks something.
- List the third-party scripts your pages load, who can change them, and remove the ones you no longer need.
- Write one permission test: can one customer reach another customer's records?
- Run Claude Code's `/security-review` on your branch before you commit, so risky settings (such as a site config that publishes raw HTML as-is), hardcoded secrets and personal data get flagged before they ship. Read what it says it covered before you trust "no vulnerabilities found," check each lead yourself, and don't paste secrets into a hosted model.
- Write down what you found as a checklist you can reuse on the next app.

Security was always important. One week brought a fully automated AI attack and malicious code on 178 organizations' websites through one vendor's scripts. My bet is that the chance of any given app being probed is higher than it has been, because attacks are cheaper and more capable, and the skilled human is no longer a requirement. The same tools that lowered the attacker's cost are available to us, and as the people our users rely on, we should use them. The rest is engineering: design, review, testing, patching and recovery, built into how we ship.

## Sources

- POLITICO: [Google says Russian speakers pulled off first-ever fully automated AI cyberattack](https://www.politico.eu/article/google-says-russian-speakers-behind-first-ever-fully-automated-ai-cyberattack/): Google's report on fully automated exploitation, the attack details and the "accelerate attacks" quote
- @unusual_whales on X: [post on Google and autonomous attacks](https://x.com/unusual_whales/status/2122506553047814275): where I first saw the Google story
- Newsweek: [Cyber Attack Hits 178 Major Websites: Full List of Affected Organizations](https://www.newsweek.com/cyber-attack-websites-affected-12725863): the 178-organization list, Optimizely's statement, what its security report says about the email-guessing attempts, and the payment-card and iPhone/iPad details
- @HormuzLetter on X: [post on the Optimizely Web attack](https://x.com/HormuzLetter/status/2122535982591365248): where I first saw the Optimizely story
- @KobeissiLetter on X: [post on the NSA Net outage](https://x.com/KobeissiLetter/status/2122715520281743849): where I first saw the NSANet outage
- CNN: [NSA highly classified network outage](https://www.cnn.com/2026/11/20/politics/nsa-highly-classified-network-outage-resolved): the NSANet outage and its reported connection to PHP patching
- Yahoo: [CNN's syndicated report on the NSANet outage](https://nz.news.yahoo.com/outage-nsa-highly-classified-communications-140904814.html): the outage length, the PHP patching connection, and officials' statements
- Anthropic: [Claude Security](https://claude.com/product/claude-security): AI-assisted security review product
- 1Password: [1password.com](https://1password.com/): password manager
- OWASP: [Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html): structure for threat modeling
- OWASP: [Third Party JavaScript Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html): options for managing third-party scripts
- OWASP: [Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/): shared security requirements for reviews
- Snyk: [snyk.io](https://snyk.io/): code, dependency, container and infrastructure scanning
- ZAP: [Getting Started](https://www.zaproxy.org/getting-started/): testing a running web application
