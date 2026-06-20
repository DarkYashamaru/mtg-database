# MTG Commander Archetype Classifier
Task: Classify a single MTG card into Commander archetypes by assigning independent scores (0-100) based on active strategic support. 

## Scoring Guide
- 90–100: Archetype staple, core engine, or build-around payoff.
- 70–89: Strong active synergy/support.
- 40–69: Clear secondary or niche utility.
- 0: No direct interaction (default for unrelated categories).

## Archetype Reference List
1. combo: Enables infinite loops, untap engines, generic cost reductions, or deterministic wins.
2. voltron: Enhances/protects a single creature (Equipment, Auras, Hexproof, Double Strike).
3. control: Reactive answers, spot removal, counterspells, board wipes, instant-speed card draw.
4. stax_taxes: Resource restriction, taxing effects, search prevention, hatebears.
5. aristocrats: Sacrifice outlets, death triggers, recurring sacrifice/grave loops.
6. spellslinger: Rewards casting or copies instants/sorceries (Magecraft).
7. storm: High spell-velocity in a single turn, rituals, cost reducers.
8. go_wide_tokens: Generates, doubles, or anthems large counts of creature tokens.
9. tribal_kindred: Direct mechanical references or rewards for specific creature types.
10. aggro_combats: Extra combat phases, high-tempo combat pressure, haste.
11. burn_slug: Direct or symmetrical group damage/punishment triggers.
12. group_hug_politics: Symmetrical draw/ramp, voting, goad, political incentives.
13. pillowfort: Taxing opponents' attacks, defense networks, combat prevention.
14. reanimator: Graveyard recursion, self-mill engines, discard outlets for high-cmc targets.
15. landfall: Triggers directly on lands entering the battlefield.
16. lands_matter: Non-basic land utility, land sacrifice, land recursion.
17. stompy: Power scaling, oversized creatures, trample payoffs.
18. blink_flicker: Temporary exile and return effects to reuse ETB triggers.
19. artifacts: High affinity, metalcraft, artifact token loops, or artifact sacrifice.
20. enchantments: Constellation, enchantress draw engines, aura/enchantment synergies.
21. superfriends: Planeswalker loyalty manipulation, proliferation, planeswalker search.
22. wheels_discard: Forced discard/draw loops, madness, cycling payoffs.
23. counters: Manipulates or scales off +1/+1, -1/-1, charge, or proliferation counters.
24. theft_clones_aikido: Copying spells, clone effects, redirecting opposing resources.
25. cheat_cascade: Bypassing mana costs, cascade, discover, cheating cards into play.
26. alt_win: Explicit "you win" or "opponents lose" clauses.
27. lifegain_drain: Continuous lifegain triggers, resource conversion via life-pay, or drain.
28. mill: Directly deleting cards from libraries into graveyards.
29. tribal_plus: Niche mechanics like Defenders, Morph/face-down, or Historic/Legends matter.
30. relentless_colony: Bypasses deck construction limits ("any number of this card").

## Input Data Rules
- Prioritize Oracle Text over external tag names if conflicts arise.
- Cross-reference tags: If an explicit tag exists (e.g., `synergy-equipment`), the corresponding category (`voltron`) must be non-zero.
- High raw power or general card advantage does not warrant a high archetype score on its own.
- Output requirements are strictly enforced by the structural JSON configuration profile.