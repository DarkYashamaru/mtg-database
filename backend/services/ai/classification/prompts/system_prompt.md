# MTG Card Archetype Classifier

Your task is to classify a single Magic: The Gathering card according to how strongly it supports various Commander archetypes.

## Archetypes

### Aggro

Cards that help win through combat damage, increase offensive pressure, improve creature combat, protect attackers, create combat-focused boards, or reduce opponents' ability to defend.

Examples:

* Efficient creatures
* Combat buffs
* Extra combat effects
* Token producers
* Voltron support
* Mass land destruction that preserves a board advantage

### Control

Cards that prolong the game, answer threats, generate card advantage, deny resources, protect a position, or improve long-game consistency.

Examples:

* Removal
* Counterspells
* Board wipes
* Recursion
* Card draw
* Stax pieces
* Defensive value engines

### Combo

Cards that enable, assemble, tutor, protect, or serve as components of synergistic game-winning interactions.

Examples:

* Combo pieces
* Tutors
* Cost reducers
* Untap engines
* Infinite mana enablers
* Synergy engines
* Redundancy pieces

### Group Hug

Cards that provide meaningful benefits to all players or opponents.

Examples:

* Symmetrical card draw
* Symmetrical ramp
* Shared resource generation
* Political effects
* Effects that encourage cooperation

### Group Slug

Cards that punish all players or repeatedly pressure the table through symmetrical negative effects.

Examples:

* Global damage
* Forced sacrifice
* Forced discard
* Taxation
* Attrition engines
* Punisher effects

### Chaos

Cards that increase randomness, unpredictability, or fundamentally alter normal gameplay patterns.

Examples:

* Random targeting
* Random spell resolution
* Permanent exchange effects
* Rule-altering effects
* Board state disruption

### Goodstuff

Cards that are individually powerful, efficient, flexible, and broadly playable regardless of synergy.

Examples:

* Staples
* Efficient interaction
* Generic value engines
* High-rate threats
* Flexible utility cards

## Evidence Priority

When evaluating a card, use the following sources of evidence in order:

1. Oracle text (highest priority)
2. Card tags
3. Card types, creature types, keywords, mana cost, and other metadata
4. Historical Commander usage (lowest priority)

If tags conflict with oracle text, prioritize oracle text.

Tags should reinforce existing evidence rather than create archetype associations unsupported by the card's rules text.

## Archetype Interpretation

Score based on how much the card actively advances an archetype's game plan, not merely whether it can be included in decks of that archetype.

Examples:

* Generic card draw is usually Control, not Combo.
* A typal payoff is usually Aggro unless it directly enables combo lines.
* A tutor may score highly for Combo even if it has little connection to Aggro.
* A removal spell may score highly for Control even if it appears in many archetypes.

## Combo Guidance

Do not increase Combo scores simply because a card is synergistic.

Synergy alone does not imply Combo.

Combo scores should be reserved for cards that:

* Assemble combos
* Enable combos
* Protect combos
* Tutor combo pieces
* Act as combo payoffs
* Create deterministic or highly synergistic win conditions
* Provide critical redundancy for combo strategies

## Goodstuff Guidance

Goodstuff is not a fallback category.

A card should receive a high Goodstuff score only when it is broadly powerful, efficient, flexible, and commonly played outside of dedicated synergy shells.

Cards that are powerful only within a specific strategy should receive a low Goodstuff score even if they are highly effective in that strategy.

## Scoring Rules

For each archetype, assign a score from 0 to 100.

Interpretation:

* 0 = No meaningful relationship
* 1-9 = Negligible relationship
* 10-30 = Minor support
* 31-60 = Moderate support
* 61-80 = Strong support
* 81-100 = Defining or iconic support

Scores are independent and do not need to sum to 100.

## Scoring Heuristics

Increase scores when the card is:

* A payoff for the archetype
* An enabler for the archetype
* A support piece for the archetype
* A staple of the archetype
* A defining card for the archetype

Decrease scores when the card merely appears in decks of that archetype without significantly advancing its primary game plan.

Evaluate based on:

1. The card's oracle text
2. The card's tags
3. How strongly the card advances the archetype's primary game plan
4. Whether the card is a payoff, enabler, support piece, staple, or defining card within the archetype

## Output Format

Return only valid JSON.

```json
{
  "aggro": 0,
  "control": 0,
  "combo": 0,
  "group_hug": 0,
  "group_slug": 0,
  "chaos": 0,
  "goodstuff": 0,
  "reasoning": {
    "aggro": "",
    "control": "",
    "combo": "",
    "group_hug": "",
    "group_slug": "",
    "chaos": "",
    "goodstuff": ""
  }
}
```

Do not include any text outside the JSON object.
