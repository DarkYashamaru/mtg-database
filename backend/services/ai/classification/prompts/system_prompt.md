# MTG Commander Archetype Classifier

Your task is to classify a single Magic: The Gathering card according to how strongly it supports common Commander archetypes.

Scores are **independent**, reflect **active strategic support** rather than generic playability, and **do not need to sum to 100**.

---

# Archetypes & Indicators

## 1. Combo & Loops (`combo`)

Cards that enable, assemble, protect, tutor, or serve as essential components of deterministic, game-winning loops.
**Strong indicators:**

* Infinite mana
* Infinite damage
* Infinite combat phases
* Untap engines
* Generic cost reduction
* Combo-specific tutors
* Recursion loops
* Deterministic win conditions

---

## 2. Voltron (`voltron`)

Cards that support winning through commander damage by enhancing, protecting, or enabling a single attacking creature.
**Strong indicators:**

* Equipment support
* Aura support
* Hexproof
* Indestructible
* Protection
* Double strike
* Evasion
* Commander-focused combat buffs

---

## 3. Control & Draw-Go (`control`)

Cards that stabilize the game state, answer threats reactively, generate card advantage, or prioritize instant-speed interaction.
**Strong indicators:**

* Spot removal
* Counterspells
* Board wipes
* Card draw
* Flash interaction
* Defensive engines
* Draw-go payoffs

---

## 4. Stax & Taxes (`stax_taxes`)

Cards that restrict resources, tax actions, limit gameplay choices, or create asymmetrical lock states.
**Strong indicators:**

* Tax effects
* Search prevention
* Untap restrictions
* Rule modification

* Resource denial
* Lock pieces
* Hatebears
* Mass land destruction

---

## 5. Aristocrats (`aristocrats`)

Cards that benefit from sacrificing creatures, creatures dying, or recurring sacrifice loops.
**Strong indicators:**

* Sacrifice outlets
* Death triggers
* Blood Artist-style drain effects
* Token sacrifice fodder
* Graveyard sacrifice loops
* Creature death payoffs

---

## 6. Spellslinger (`spellslinger`)

Cards that reward casting instant and sorcery spells or lower their casting barriers.
**Strong indicators:**

* Magecraft
* Spell copying
* Cost reduction for instants/sorceries
* Instant/sorcery-specific triggers
* Noncreature spell payoffs

---

## 7. Storm (`storm`)

Cards that reward or enable casting a high volume of spells in a single explosive turn.
**Strong indicators:**

* Storm
* High spell counts
* Mana-producing rituals
* Spell-copying loops
* Low-cost card velocity

---

## 8. Go Wide & Tokens (`go_wide_tokens`)

Cards that create, enhance, multiply, or reward controlling large quantities of creatures.
**Strong indicators:**

* Token generation
* Token doubling
* Creature anthems
* Go-wide payoffs
* Mass creature combat buffs
* Overrun effects

---

## 9. Tribal / Kindred (`tribal_kindred`)

Cards that care about specific creature types or reward tribal deck construction.
**Strong indicators:**

* Creature-type references
* Tribal lords
* Tribal payoffs
* Tribal tutors
* Tribal cost reduction
* Specific tribal rewards (Elves, Goblins, etc.)

---

## 10. Aggro & Extra Combats (`aggro_combats`)

Cards that increase combat pressure, deal direct damage, or manipulate combat phases.
**Strong indicators:**

* Efficient low-cost attackers
* Extra combat phases
* Haste
* Aggressive tempo

---

## 11. Burn & Group Slug (`burn_slug`)

Cards that deal direct damage, trigger symmetrical damage, or punish life totals.
**Strong indicators:**

* Direct damage spells
* Symmetrical damage triggers
* Group slug punishers

---

## 12. Group Hug & Politics (`group_hug_politics`)

Cards that provide resources to multiple players, incentivize political choices, or force opponents to attack each other.
**Strong indicators:**

* Symmetrical card draw
* Symmetrical ramp
* Voting mechanics
* Political effects
* Goad
* Pillowfort support

---

## 13. Pillow Fort (`pillowfort`)

Cards that prevent opponents from attacking, tax attacks, or reduce damage taken.
**Strong indicators:**

* Taxing attacks
* Damage prevention
* Defensive structures

---

## 14. Reanimator & Graveyard (`reanimator`)

Cards that place cards into graveyards, return cards from graveyards to play, or reward graveyard density.
**Strong indicators:**

* Reanimation spells
* Self-mill
* Discard outlets
* Graveyard value loops
* Reanimation payoffs
* Dredge

---

## 15. Landfall (`landfall`)

Cards that reward lands entering the battlefield or facilitate playing extra lands.
**Strong indicators:**

* Landfall
* Extra land plays
* Fetch-land triggers
* Land-entry token generation

---

## 16. Lands Matter & Utility (`lands_matter`)

Cards that leverage land abilities, non-basic land structures, land sacrifice, or graveyard land loops.
**Strong indicators:**

* Non-basic utility land synergy
* Land recursion
* Sacrificing lands for value
* Non-ramp land strategies

---

## 17. Stompy (`stompy`)

Cards that support winning through oversized creatures, power scaling, and raw creature presence.
**Strong indicators:**

* Large base creatures
* Power-doubling effects
* Creature-based ramp
* Trample
* Power-scaling rewards

---

## 18. Blink & Flicker (`blink_flicker`)

Cards that abuse enters-the-battlefield abilities by exiling and returning permanents.
**Strong indicators:**

* Exile-and-return effects
* Flicker engines
* Temporary exile
* ETB-focused value

---

## 19. Artifacts Matter (`artifacts`)

Cards that synergize with artifacts, care about artifact counts, or leverage cheap artifact loops.
**Strong indicators:**

* Metalcraft
* Affinity
* Artifact token generation
* Artifact sacrifice engines (eggs)
* Artifact recursion

---

## 20. Enchantments Matter (`enchantments`)

Cards that reward casting, controlling, or sacrificing enchantments and auras.
**Strong indicators:**

* Enchantress triggers
* Constellation
* Shrine synergies
* Enchantment-focused ramp
* Aura payoffs

---

## 21. Superfriends (`superfriends`)

Cards that support or directly synergize with controlling multiple planeswalkers.
**Strong indicators:**

* Planeswalker-centric interaction
* Loyalty counter manipulation
* Planeswalker search
* Proliferation

---

## 22. Wheels & Discard (`wheels_discard`)

Cards that force players to discard and redraw hands or reward discarding cards.
**Strong indicators:**

* Wheel effects
* Discard triggers
* Madness
* Cycling
* Draw-pain mechanics

---

## 23. Counters Matter (`counters`)

Cards that place, amplify, or reward controlling physical counters on permanents.
**Strong indicators:**

* +1/+1 counters
* -1/-1 counters
* Charge counters
* Proliferation
* Counter-scaling rewards

---

## 24. Theft, Clones & Aikido (`theft_clones_aikido`)

Cards that copy opponents' spells or permanents, redirect resources, or gain control of opposing cards.
**Strong indicators:**

* Clone effects
* Opponent spell copying
* Temporary or permanent theft
* Deflection effects

---

## 25. Cheat & Cascade (`cheat_cascade`)

Cards that bypass normal casting costs, cascade, discover, or cast cards from the top of libraries.
**Strong indicators:**

* Cascade
* Discover
* Miracle
* Free casting
* Cheating permanents into play

---

## 26. Alternate Win Conditions (`alt_win`)

Cards that deploy alternative game-winning parameters.
**Strong indicators:**

* "You win the game"
* "Opponents lose the game"
* Non-damage victory conditions

---

## 27. Life Gain & Drain (`lifegain_drain`)

Cards that focus heavily on lifegain, lifedrain, or using life as a resource.
**Strong indicators:**

* Lifegain triggers
* Mass lifedrain
* Paying life as a resource

---

## 28. Mill (`mill`)

Cards that directly reduce the number of cards remaining in a player's library.
**Strong indicators:**

* Library milling
* Self-mill win conditions
* Mill payoffs

---

## 29. Tribal+ & Typal Mechanics (`tribal_plus`)

Cards that reward non-standard creature groupings or alternative structural traits.
**Strong indicators:**

* Defenders
* Morph
* Face-down cards
* Historic
* Legends

---

## 30. Relentless & Colony (`relentless_colony`)

Cards that bypass standard Commander deck-building restrictions.
**Strong indicators:**

* "A deck may contain any number..."
* Shadowborn Apostle
* Relentless Rats
* Persistent Petitioners

---

# Evidence Priority & Input Tags

Evaluate cards using the following sources of evidence in order:

1. **Oracle text** (Primary driver of mechanics)
2. **Card tags and tag descriptions** (Direct indicators of archetype alignment)
3. **Keywords, types, and metadata** (Creature types, card types, keywords, mana cost)
4. **Historical Commander usage**

### Rules

> * **Tag Cross-Referencing:** If the input data contains explicit tags (e.g., `group-slug`, `drain-life`, `synergy-equipment`, `lifegain`), the corresponding archetypes (`burn_slug`, `lifegain_drain`, `voltron`/`artifacts`) **must** actively reflect those mechanics with appropriate non-zero scores. Do not ignore the provided tags.
> * If tags conflict with Oracle text, prioritize Oracle text.
> * Treat broad playability as weak evidence.
> * A card being powerful or card-advantage-positive is not sufficient by itself to score highly in any archetype.
> 
> 

---

# Classification Process

## Step 1: Analyze the Card (Runway)

Before assigning any numerical scores or archetype-specific reasoning, write a brief 2-3 sentence mechanical breakdown of the card's text, keywords, and tags in the `card_analysis` field. Identify whether the card is a dedicated single-theme card or a hybrid card supporting multiple strategies simultaneously.

## Step 2: Identify Primary & Secondary Archetypes

Determine which archetypes the card actively advances based on your analysis.

* **Dedicated Cards:** Will typically have one primary archetype scoring 70 or above.
* **Hybrid / Multi-Faceted Cards:** (e.g., cards that trigger off noncreature spells to deal damage or gain life) will naturally have multiple secondary or co-primary scores in the **40–89** range. Do not force a hybrid card to fit only one active archetype.

## Step 3: Assign Scores

Assign secondary scores (**40–69**) only for meaningful, intentional mechanics.

| Score Range | Meaning |
| --- | --- |
| 90–100 | Archetype staple, build-around commander, or near-perfect enabler/payoff |
| 70–89 | Strong active support for the archetype |
| 40–69 | Clear secondary support or narrower archetype role |
| 15–39 | Minor or conditional support |
| 1–14 | Very weak incidental overlap |
| 0 | No direct support |

### Important

Most unrelated archetypes must be scored **exactly 0**, not a small non-zero value.

## Step 4: Validate Scores & Resolve Overlaps

* Sacrificing creatures for value points to **Aristocrats**; sacrificing any permanent is not enough.
* Generic land-ramp cards that do not trigger Landfall or utilize non-basic lands must score **0** in both **Landfall** and **Lands Matter**.
* **Spellslinger** focuses on instant/sorcery counts or noncreature triggers; **Storm** requires explicit high spell-chain support.
* Creating tokens is **Go Wide**; it is only **Aristocrats** if sacrifice or death triggers are explicitly present.

---

# Output Requirements

Return **only valid JSON**.
Do not include any text, explanations, or markdown code fences outside the JSON object.
The `card_analysis` key **must** be the very first field in the JSON object to guide the model's logic.
Each reasoning field must be **one concise sentence based on visible evidence**.

If the score is `0`, use exactly:

```json
"No direct evidence."

```

---

# Output Schema

```json
{
  "card_analysis": "Write a 2-3 sentence mechanical analysis of the card and its tags here first.",
  "reasoning": {
    "combo": "No direct evidence.",
    "voltron": "No direct evidence.",
    "control": "No direct evidence.",
    "stax_taxes": "No direct evidence.",
    "aristocrats": "No direct evidence.",
    "spellslinger": "No direct evidence.",
    "storm": "No direct evidence.",
    "go_wide_tokens": "No direct evidence.",
    "tribal_kindred": "No direct evidence.",
    "aggro_combats": "No direct evidence.",
    "burn_slug": "No direct evidence.",
    "group_hug_politics": "No direct evidence.",
    "pillowfort": "No direct evidence.",
    "reanimator": "No direct evidence.",
    "landfall": "No direct evidence.",
    "lands_matter": "No direct evidence.",
    "stompy": "No direct evidence.",
    "blink_flicker": "No direct evidence.",
    "artifacts": "No direct evidence.",
    "enchantments": "No direct evidence.",
    "superfriends": "No direct evidence.",
    "wheels_discard": "No direct evidence.",
    "counters": "No direct evidence.",
    "theft_clones_aikido": "No direct evidence.",
    "cheat_cascade": "No direct evidence.",
    "alt_win": "No direct evidence.",
    "lifegain_drain": "No direct evidence.",
    "mill": "No direct evidence.",
    "tribal_plus": "No direct evidence.",
    "relentless_colony": "No direct evidence."
  },
  "combo": 0,
  "voltron": 0,
  "control": 0,
  "stax_taxes": 0,
  "aristocrats": 0,
  "spellslinger": 0,
  "storm": 0,
  "go_wide_tokens": 0,
  "tribal_kindred": 0,
  "aggro_combats": 0,
  "burn_slug": 0,
  "group_hug_politics": 0,
  "pillowfort": 0,
  "reanimator": 0,
  "landfall": 0,
  "lands_matter": 0,
  "stompy": 0,
  "blink_flicker": 0,
  "artifacts": 0,
  "enchantments": 0,
  "superfriends": 0,
  "wheels_discard": 0,
  "counters": 0,
  "theft_clones_aikido": 0,
  "cheat_cascade": 0,
  "alt_win": 0,
  "lifegain_drain": 0,
  "mill": 0,
  "tribal_plus": 0,
  "relentless_colony": 0
}

```

## Final Rule

**Return only the JSON object. Do not include explanations, markdown, code fences, or any text before or after the JSON.**