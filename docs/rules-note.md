# Kamir — Momir Basic Rules Note

This document explains what Momir Basic is, what Kamir needs to implement, and what it
explicitly does not need to implement.

---

## What is Momir Basic?

Momir Basic is a Magic: The Gathering format created around the Momir Vig, Simic Visionary
vanguard avatar. The format rules are:

- Each player's deck consists of exactly 60 basic lands (any mix of types).
- Each player begins the game with the Momir Vig vanguard avatar, which grants the ability:
  **"{X}, Discard a card: Put a token onto the battlefield that's a copy of a creature card
  with mana value X chosen at random from among all creature cards. Activate this ability
  only any time you could cast a sorcery and only once each turn."**
- In practice: pay X mana, discard one land from hand → get a random creature token with
  mana value X.

In a paper implementation (as Kamir supports), players agree to use these rules informally.
A printed card serves as the token and identifies the creature.

---

## What Kamir Implements

Kamir implements only the mechanical core of the format that requires software support:

| Requirement | Implemented by |
|---|---|
| Maintain a pool of all eligible creatures by mana value | Database Builder |
| Accept a mana value and select one creature uniformly at random | Play App |
| Display the selected creature's name, type, oracle text, and P/T | Play App |
| Print a readable card slip as the token | Printing/Rendering |

---

## What Kamir Does NOT Implement

Kamir is **not** a rules engine. The following are handled by the players themselves:

- **Mana tracking**: players count their own mana pool.
- **Land discard confirmation**: Kamir does not verify the player has a land to discard.
- **Stack and priority**: Kamir does not model the stack.
- **Combat**: attack declarations, blocking, damage assignment are done by the players.
- **Life totals**: players track their own life points.
- **Triggered abilities**: if the selected creature has "enters the battlefield" triggers,
  players resolve them manually using the rules text on the printed slip.
- **State-based actions**: handled manually.
- **Turn structure enforcement**: Kamir does not enforce the "once per turn" or "sorcery speed"
  restrictions. Players self-police.

---

## Creature Pool Eligibility Rules

The card pool stored in `kamir_cardpool.sqlite` must match what would be in "all creature cards"
for the format. Kamir applies the following filters:

- **Type**: must be a Creature (or have "Creature" in its type line as a front face).
- **Mana value**: 0 to 15 inclusive (whole numbers only; split card values are not used).
- **Sets**: limited to the allowed set list in `config.toml`. Joke sets (e.g., Unglued,
  Unhinged, Unfinity) are excluded.
- **Uniqueness**: each distinct creature name appears at most once in the pool.
  If a creature has been reprinted, only the first printing is included. This is the
  standard Momir Basic rule: each unique creature appears once, regardless of how many
  times it has been printed.
- **Front face only**: for double-faced cards, only the front face is considered. The
  printed slip shows the front face's stats.
- **Base set only**: cards with a collector number beyond the base set size (e.g., bonus
  sheet cards, promo variants) are excluded.

---

## Design Implication: No Rules Engine Needed

Because Kamir only selects a random creature and prints a slip, it never needs to:

- Parse oracle text for machine execution.
- Know whether a creature has "flying" vs. "lifelink" mechanically.
- Track game state.

Oracle text is stored and printed as a human-readable string only. Players read the text
on the slip and apply the rules themselves, exactly as they would with any paper MTG token.

This keeps Kamir's implementation simple and its card pool accurate: as long as the filter
logic correctly classifies which cards are Momir-eligible, the tool is correct.
