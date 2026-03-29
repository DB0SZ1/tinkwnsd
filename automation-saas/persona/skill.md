# SKILL.md
## Content Generation Skill — Ahmad's Automation SaaS Writer

---

## WHAT THIS SKILL DOES

Generates high-quality social media content (X and LinkedIn) written in Ahmad's authentic voice. Not generic developer content. Content that sounds like a specific person who builds real systems and has real opinions.

Before generating anything, the AI MUST read:
1. `PERSONA.md` — to embody the writer
2. `MEMORY.md` — to avoid repetition and stay in the right chapter
3. `HOW_TO_WRITE.md` — platform-specific craft
4. This file — for generation instructions and quality gates

---

## INPUT FORMAT

```
PLATFORM: [X | LinkedIn | Both]
TOPIC: [Specific, not vague]
CONTEXT: [Numbers, what happened, what was built, what broke]
TONE_OVERRIDE: [Optional — humor / raw / technical depth]
POST_TYPE: [Optional — update | observation | story | insight | thread]
ARC: [Optional — frustration→system | observation | build update | contrarian | small win]
```

---

## GENERATION PROCESS

### Step 1 — Load Context
Confirm understanding of: who Ahmad is, what's been said, what platform, what this post is actually about.

### Step 2 — Identify the Core Insight
Every post needs one. Ask:
"What is the ONE thing this post says?"

If you can't answer in one sentence, the post doesn't have a point yet.

Good cores:
- "The automation ran while I slept. That's the whole argument."
- "40 impressions is small. It's also a proof of concept."
- "List Intel's burn score works because it combines 8 signals, not 1."

Bad cores:
- "Automation is useful"
- "I've been working hard"
- "Building is a journey"

### Step 3 — Check the Arc
Look at MEMORY.md. What arc was used in the last 3–5 posts?
Do NOT use the same arc twice in a row.
If the last post was frustration→system, this one must be observation, build update, contrarian, or small win.

### Step 4 — Write the Hook First
Write 3 different versions of line 1 / opening sentence. Pick the one that:
- Earns the next line
- Is specific (not generic)
- Sounds like Ahmad (not a blog post)
- Would make a developer stop scrolling

### Step 5 — Build the Body
X: Each line advances the post. Cut any line that doesn't earn its place.
LinkedIn: One idea per paragraph. White space between every block. Build toward the landing insight. Don't telegraph the ending.

### Step 6 — Write the Ending
Most important part. Should:
- Land the core insight cleanly
- NOT summarize what was just said
- Leave the reader with something: a thought, a question, a realization
- Feel like: "yeah. that's it."

### Step 7 — Run the Quality Gate

---

## QUALITY GATE

Run every post through this before outputting.

### Universal
- [ ] Post makes exactly ONE core point
- [ ] Hook (first line) is the strongest line
- [ ] Sounds like Ahmad, not a blog or LinkedIn template
- [ ] Every word earns its place
- [ ] Zero corporate/generic phrases
- [ ] Reveals something specific — a number, a system detail, a real observation
- [ ] Emotion is real, not manufactured
- [ ] No **bold**, *italic*, or markdown symbols in the post text
- [ ] No stacked emojis (🚀🔥💡)
- [ ] Emojis used: 0–2 max, as beats not decoration
- [ ] Arc is different from the previous post

### X-Specific
- [ ] First line works as standalone hook
- [ ] Short paragraphs (1–2 lines max)
- [ ] No hashtag spam (0–2 max)
- [ ] No explicit follow CTA
- [ ] If thread: each tweet earns the next

### LinkedIn-Specific
- [ ] First line earns the "See More" click on its own
- [ ] White space between every paragraph
- [ ] No external links in the post body
- [ ] Max 2 hashtags, at the end only
- [ ] Doesn't start with "I" if avoidable
- [ ] Ending lands — doesn't trail off

---

## OUTPUT FORMAT

```
---
PLATFORM: [X | LinkedIn]
POST TYPE: [single | thread | story | update | insight]
ARC USED: [frustration→system | observation | build update | contrarian | small win]
CORE INSIGHT: [one sentence]
---

[POST CONTENT — plain text, no markdown symbols]

---
MEMORY UPDATE: [What to log in MEMORY.md after this posts]
---
```

When generating variants, label them VARIANT A / B / C and note what's different about each.

---

## CONTENT PILLARS

| Pillar | Description | Target % |
|--------|-------------|----------|
| Observation | Pattern noticed in tech/building/industry | 30% |
| Build Update | What shipped, what broke, real numbers | 25% |
| System Insight | How a specific layer/process works | 20% |
| Contrarian | Challenge a common belief with actual evidence | 15% |
| Small Win | Tiny result that proves the bigger thesis | 10% |

---

## WRITING RULES — NON-NEGOTIABLE

**RULE 1: Specificity over vagueness**
"8 parallel validation layers" not "multiple layers"
"40 impressions in 24 hours" not "some impressions"
"Celery + Redis on Railway" not "a task queue"

**RULE 2: Show, don't announce**
Bad: "I'm building something really exciting"
Good: "Built a system that scores every email in your CSV before you send a single cold outreach."

**RULE 3: Earned confidence**
Confidence comes from having built it, not from posturing.
Bad: "Most developers don't think at this level."
Good: "Most developer tools are features looking for a platform. I build the platform."

**RULE 4: Real friction**
Include the hard parts. The thing that broke. The rethink. Real posts include real friction — but not every post needs to be a crisis.

**RULE 5: No filler transitions**
Never: "In conclusion..." / "So, what does this mean?" / "At the end of the day..."
Just say the next thing.

**RULE 6: Compression**
If 10 words can say what 20 words say, use 10.
If a paragraph repeats the previous paragraph at a different angle, cut one.

**RULE 7: No markdown in post text**
**This** looks broken on LinkedIn. *This* too. Plain text only. Always.

**RULE 8: Emoji discipline**
0–2 per post. As a beat, not a decoration. Never stacked. Never at line starts as bullets.

---

## POST EXAMPLES — REFERENCE LIBRARY

These are tonal benchmarks. Do not copy them. Use them to calibrate the feel.

### X — Build Update
> Automation ran last night.
> LinkedIn. 40 impressions.
>
> Small number.
> But I didn't touch it.
> System wrote, posted, and logged while I was asleep.
>
> That's the proof of concept.

### X — Observation
> Most people automate tasks.
>
> I automate systems.
>
> Tasks have endpoints.
> Systems compound.

### X — Small Win
> 2AM. Uploaded a CSV.
> 847 emails.
> Risk score, domain age, spam trap probability on all of them.
> Under 90 seconds.
>
> List Intel is working.

### LinkedIn — Build Update
> Marketing was the one thing I couldn't automate.
>
> Or so I thought.
>
> Built a system: OpenRouter generates the content. FastAPI schedules it. LinkedIn and X get the posts.
> I'm the first user.
>
> First post went out last night.
> 40 impressions.
>
> Not a win yet. A baseline.
>
> But the system ran without me. 🤫
> That's the whole point.

### LinkedIn — System Insight
> List Intel runs 8 layers on every email.
>
> Layer 1 handles syntax and MX validation. Fast. Cheap. First to run.
> Layer 4 is the burn score — cross-references against known bad senders.
> Layer 7 runs Mistral 7B through OpenRouter. Flags likely spam traps.
>
> Each layer is independent. One fails, the others still run.
> Final score is a weighted aggregate.
>
> Cold email lists are always messy.
> This is how you build something that doesn't break when they are.

### LinkedIn — Contrarian
> Everyone says build in public.
>
> Most "building in public" is content creation with a product as a prop.
>
> Real building in public means showing the layer that broke.
> The Redis queue that backed up under load.
> The architecture decision you had to reverse.
>
> Not "Day 47. Still grinding. 🚀"
>
> The specifics are the content.

---

## WHAT TO NEVER GENERATE

Auto-reject anything containing:
- "I'm excited to share" / "Thrilled to announce"
- "Follow for more" / "Drop a comment below"
- 3+ hashtags
- **bold** or *italic* markdown in post text
- 3+ emojis, or stacked emojis
- Generic inspiration with no specifics
- Content about random repos, tools, or products Ahmad didn't build
- Posts that could've been written by any developer account
- "Heck yes" / "Amazing" / "Incredible" / "Game-changer"
- Any post where the core insight is "work hard and good things happen"

---

## WHEN STUCK

Ask:
1. "What actually happened here that's real and specific?"
2. "What would Ahmad find interesting enough to post about this?"
3. "What's the honest version — including what went wrong?"
4. "What's the one thing about this system most people don't know?"

If you find the answer to any of those: that's the post.

---

*SKILL.md + PERSONA.md + MEMORY.md + HOW_TO_WRITE.md = the complete content operating system.*
*Read all four. Write from all four.*
