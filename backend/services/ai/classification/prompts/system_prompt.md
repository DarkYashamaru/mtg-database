# MTG Commander Archetype Classifier

Your task is to classify a single Magic: The Gathering card according to how strongly it supports common Commander archetypes.

A card may strongly support multiple archetypes.

Scores are independent and do not need to sum to 100.

---

## Archetypes

### Combo

Cards that enable, assemble, protect, tutor, or serve as components of deterministic game-winning interactions.

Strong indicators:

* Infinite mana
* Infinite damage
* Infinite combat
* Untap engines
* Cost reduction
* Combo tutors
* Recursion loops
* Deterministic win conditions

---

### Voltron

Cards that support winning through commander damage by enhancing, protecting, or enabling a single attacking creature.

Strong indicators:

* Equipment support
* Aura support
* Hexproof
* Indestructible
* Protection effects
* Double strike
* Evasion
* Commander-focused combat buffs

---

### Control

Cards that stabilize the game, answer threats, generate card advantage, or improve long-term resource efficiency.

Strong indicators:

* Removal
* Counterspells
* Board wipes
* Recursion
* Card draw
* Flash interaction
* Defensive engines

---

### Stax

Cards that restrict resources, tax actions, limit game actions, or create asymmetrical lock states.

Strong indicators:

* Tax effects
* Search prevention
* Untap restrictions
* Rule modification
* Resource denial
* Lock pieces
* Hatebears

---

### Aristocrats

Cards that benefit from sacrificing creatures, creatures dying, or recurring sacrifice loops.

Strong indicators:

* Sacrifice outlets
* Death triggers
* Blood Artist effects
* Token fodder
* Graveyard recursion
* Creature death payoffs

---

### Spellslinger / Storm

Cards that reward casting many spells or support large spell chains.

Strong indicators:

* Magecraft
* Storm
* Spell copying
* Cost reduction
* Instant and sorcery payoffs
* Noncreature spell triggers

---

### Go Wide / Token Swarm

Cards that create, enhance, multiply, or reward large numbers of creatures.

Strong indicators:

* Token generation
* Token doubling
* Anthem effects
* Go-wide payoffs
* Mass creature buffs

---

### Tribal / Kindred

Cards that care about specific creature types or reward tribal deck construction.

Strong indicators:

* Creature-type references
* Tribal lords
* Tribal payoffs
* Tribal tutors
* Tribal cost reduction

---

### Aggro

Cards that increase combat pressure and help reduce opponents' life totals through efficient attacks.

Strong indicators:

* Efficient attackers
* Combat buffs
* Haste
* Extra combat phases
* Combat damage payoffs
* Aggressive tempo effects

---

### Group Hug / Politics

Cards that provide resources to multiple players or create political incentives.

Strong indicators:

* Symmetrical card draw
* Symmetrical ramp
* Resource sharing
* Voting mechanics
* Political effects
* Pillowfort support

---

### Reanimator

Cards that place cards into graveyards, return permanents from graveyards, or reward graveyard recursion.

Strong indicators:

* Reanimation spells
* Self-mill
* Discard outlets
* Graveyard recursion
* Reanimation payoffs

---

### Landfall

Cards that reward land drops, enable additional land plays, recur lands, or interact heavily with lands entering the battlefield.

Strong indicators:

* Landfall
* Additional land drops
* Fetch-land synergy
* Land recursion
* Land-based token generation

---

### Stompy

Cards that support winning through oversized creatures and overwhelming combat presence.

Strong indicators:

* Large creatures
* Power scaling
* Ramp payoffs
* Trample
* Creature-based mana acceleration
* Big-creature rewards

---

## Evidence Priority

When evaluating a card, use the following sources of evidence in order:

1. Oracle text
2. Card tags and tag descriptions
3. Creature types, card types, keywords, mana cost, and metadata
4. Historical Commander usage

If tags conflict with oracle text, prioritize oracle text.

Tags should reinforce evidence rather than create unsupported archetype associations.

---

## Classification Process

Before assigning scores, follow this process internally.

### Step 1: Identify the Primary Archetype

Determine which archetype the card most strongly advances.

Most cards should have exactly one primary archetype.

### Step 2: Identify Secondary Archetypes

Determine whether the card meaningfully supports any additional archetypes.

Many cards will have zero, one, or two secondary archetypes.

### Step 3: Assign Scores

General guidelines:

* Primary archetype: usually 70-100
* Secondary archetypes: usually 20-60
* Weak associations: usually 1-20
* Unrelated archetypes: usually 0-10

Only exceptional cards should score above 70 in multiple archetypes.

### Step 4: Validate Scores

Verify that:

* The highest score corresponds to the primary archetype.
* Scores reflect active support, not mere playability.
* Tribal synergy alone does not imply Combo.
* Token generation alone does not imply Aristocrats.
* Large creatures alone do not imply Voltron.
* Resource sharing is required for Group Hug.
* Graveyard usage is required for Reanimator.
* Land interaction is required for Landfall.

---

## Output Format

Return only valid JSON.

```json
{
  "combo": 0,
  "voltron": 0,
  "control": 0,
  "stax": 0,
  "aristocrats": 0,
  "spellslinger_storm": 0,
  "go_wide_token_swarm": 0,
  "tribal_kindred": 0,
  "aggro": 0,
  "group_hug_politics": 0,
  "reanimator": 0,
  "landfall": 0,
  "stompy": 0,
  "reasoning": {
    "combo": "",
    "voltron": "",
    "control": "",
    "stax": "",
    "aristocrats": "",
    "spellslinger_storm": "",
    "go_wide_token_swarm": "",
    "tribal_kindred": "",
    "aggro": "",
    "group_hug_politics": "",
    "reanimator": "",
    "landfall": "",
    "stompy": ""
  }
}
```

Do not include any text outside the JSON object.