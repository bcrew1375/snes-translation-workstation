# Battle action records

This document records the English-only identity layer for the battle action name
and record tables in bank `$84`. It intentionally does not reproduce the source
glyph streams. The user-supplied ROM and the ignored local renderer sheet remain
the source evidence.

## Table structure

- CPU `$84:C550-$C6CF` / ROM `$024550-$0246CF` is the 192-slot action-name
  pointer table.
- CPU `$84:CE12-$CF91` / ROM `$024E12-$024F91` is the parallel 192-slot
  action-record pointer table.
- Flat player action IDs `$00-$45` select 70 real names and records.
- IDs `$00-$1F` and `$20-$3F` form two parallel 32-action banks. They share the
  same broad sequence of energy, physical, counter, and evasive classes, but
  differ in several names, available grades, and coefficients. The tables alone
  do not prove fighter, route, or story ownership for either bank.
- IDs `$40-$45` are six exceptional state or clash-capable special actions after
  the ordinary 64-ID unlock space.
- `$46` is the shared real boundary record. `$47-$7F` repeat its record pointer
  while occupying an intentionally blank name gap. Opponent IDs `$80-$B1` use
  50 records beginning with the same boundary record.

The `label status` column distinguishes approved project terminology from direct
generic identities and provisional English working labels. A working label is an
analysis aid, not a final localization decision.

## Player IDs `$00-$1F`

| ID | English identity | Label status | Class | Lookup | Grade | Coefficient |
|---:|---|---|---:|---:|---:|---:|
| `$00` | Rapid-Fire Ki Blast | working literal | 3 | `$0A` | 0 | 200 |
| `$01` | Super Rapid-Fire Ki Blast | working literal | 3 | `$0A` | 1 | 400 |
| `$02` | Homing Ki Blast | direct | 3 | `$0B` | 0 | 300 |
| `$03` | Super Homing Ki Blast | direct | 3 | `$0B` | 1 | 600 |
| `$04` | Scatter Ki Blast | working literal | 3 | `$0C` | 0 | 150 |
| `$05` | Super Scatter Ki Blast | working literal | 3 | `$0C` | 1 | 300 |
| `$06` | Kiai Cannon | working literal | 3 | `$0D` | 0 | 250 |
| `$07` | Super Kiai Cannon | working literal | 3 | `$0D` | 1 | 750 |
| `$08` | Body Blow | direct | 0 | `$00` | 0 | 100 |
| `$09` | Power Attack | direct | 0 | `$00` | 1 | 200 |
| `$0A` | Power Charge | direct | 0 | `$00` | 2 | 600 |
| `$0B` | Dash Attack | direct | 0 | `$01` | 0 | 120 |
| `$0C` | Elbow Smash | direct | 0 | `$01` | 1 | 240 |
| `$0D` | Power Rush | direct | 0 | `$01` | 2 | 720 |
| `$0E` | Meteor Smash | direct | 0 | `$02` | 0 | 1500 |
| `$0F` | Turtle School Final Technique | working literal | 0 | `$03` | 0 | 1000 |
| `$10` | Throw | direct | 1 | `$04` | 0 | 100 |
| `$11` | Counter Throw | direct | 1 | `$04` | 1 | 200 |
| `$12` | Counter | direct | 1 | `$05` | 0 | 150 |
| `$13` | Counterattack | direct | 1 | `$05` | 1 | 300 |
| `$14` | Final Counter | direct | 1 | `$05` | 2 | 600 |
| `$15` | Afterimage Counter | direct | 1 | `$06` | 0 | 80 |
| `$16` | Super Afterimage Counter | direct | 1 | `$06` | 1 | 160 |
| `$17` | Reversal Shot | working literal | 1 | `$06` | 2 | 480 |
| `$18` | Mach Attack | direct | 2 | `$07` | 0 | 120 |
| `$19` | Dash Blow | direct | 2 | `$07` | 1 | 240 |
| `$1A` | Final Attack | direct | 2 | `$07` | 2 | 720 |
| `$1B` | Feint Attack | direct | 2 | `$08` | 0 | 150 |
| `$1C` | Feint Smash | direct | 2 | `$08` | 1 | 450 |
| `$1D` | Super Smash Blow | direct | 2 | `$08` | 2 | 900 |
| `$1E` | Afterimage Fist | working literal | 2 | `$09` | 0 | 100 |
| `$1F` | Afterimage Attack | direct | 2 | `$09` | 1 | 300 |

## Player IDs `$20-$3F`

| ID | English identity | Label status | Class | Lookup | Grade | Coefficient |
|---:|---|---|---:|---:|---:|---:|
| `$20` | Rapid-Fire Demon Light Cannon | working literal | 3 | `$0A` | 0 | 200 |
| `$21` | Super Rapid-Fire Demon Light Cannon | working literal | 3 | `$0A` | 1 | 400 |
| `$22` | Explosive Rapid-Fire Demon Light Cannon | working literal | 3 | `$0A` | 2 | 800 |
| `$23` | Homing Demon Light Cannon | working literal | 3 | `$0B` | 0 | 300 |
| `$24` | Scatter Demon Light Cannon | working literal | 3 | `$0C` | 0 | 150 |
| `$25` | Explosion Wave | working literal | 3 | `$0D` | 0 | 250 |
| `$26` | Burst Wave | working literal | 3 | `$0D` | 1 | 500 |
| `$27` | Super Burst Wave | working literal | 3 | `$0D` | 2 | 1000 |
| `$28` | Body Blow | direct | 0 | `$00` | 0 | 100 |
| `$29` | Thrust | direct | 0 | `$00` | 1 | 200 |
| `$2A` | Power Attack | direct | 0 | `$00` | 2 | 600 |
| `$2B` | Dash Attack | direct | 0 | `$01` | 0 | 120 |
| `$2C` | Elbow Smash | direct | 0 | `$01` | 1 | 240 |
| `$2D` | Power Rush | direct | 0 | `$01` | 2 | 720 |
| `$2E` | Explosive Rush | working literal | 0 | `$02` | 0 | 1000 |
| `$2F` | Super Explosive Rush | working literal | 0 | `$02` | 1 | 1500 |
| `$30` | Throw | direct | 1 | `$04` | 0 | 100 |
| `$31` | Counter Throw | direct | 1 | `$04` | 1 | 200 |
| `$32` | Final Shot | working literal | 1 | `$04` | 2 | 400 |
| `$33` | Counter | direct | 1 | `$05` | 0 | 150 |
| `$34` | Counterattack | direct | 1 | `$05` | 1 | 300 |
| `$35` | Afterimage Counter | direct | 1 | `$06` | 0 | 80 |
| `$36` | Super Afterimage Counter | direct | 1 | `$06` | 1 | 160 |
| `$37` | Reversal Shot | working literal | 1 | `$06` | 2 | 480 |
| `$38` | Dash Punch | direct, runtime corroborated | 2 | `$07` | 0 | 60 |
| `$39` | Mach Attack | direct | 2 | `$07` | 1 | 120 |
| `$3A` | Dash Blow | direct | 2 | `$07` | 2 | 240 |
| `$3B` | Feint Attack | direct | 2 | `$08` | 0 | 150 |
| `$3C` | Feint Smash | direct | 2 | `$08` | 1 | 450 |
| `$3D` | Super Smash Blow | direct | 2 | `$08` | 2 | 900 |
| `$3E` | Afterimage Fist | working literal | 2 | `$09` | 0 | 100 |
| `$3F` | Afterimage Attack | direct | 2 | `$09` | 1 | 300 |

## Exceptional player IDs `$40-$45`

| ID | English identity | Label status | Class | Lookup | Grade | Coefficient |
|---:|---|---|---:|---:|---:|---:|
| `$40` | Solar Flare | approved glossary | 5 | `$0E` | 0 | 0 |
| `$41` | Kamehameha | approved glossary | 4 | `$10` | 0 | 2000 |
| `$42` | Super Kamehameha | approved glossary | 4 | `$10` | 1 | 3000 |
| `$43` | Rage Power | working literal | 5 | `$0F` | 0 | 0 |
| `$44` | Masenko | approved glossary | 4 | `$11` | 0 | 1800 |
| `$45` | Fierce Masenko | working literal | 4 | `$11` | 1 | 3600 |

Class 4 is the only active class whose self-match matrix entry is provisional
result `$03`; these four named actions therefore identify it more precisely as the
clash-capable special-technique class. Class 5 contains zero-coefficient state or
control actions. The exceptional IDs are addressable by the name and record tables,
but progression unlock calls cover only `$00-$3F`; how `$40-$45` become selectable
remains unresolved.

## Confirmed family observations

- Repeated `(class, lookup)` pairs are presentation/combat families, not unique
  identities. Grade `+$02` orders variants within those families but remains unread
  by every confirmed direct runtime consumer.
- The two 32-action banks deliberately reuse fundamentals. Some duplicate names
  share byte-identical source streams; others have separate allocations despite the
  same rendered name.
- Player `$38` and opponent `$91` are separately allocated, byte-identical Dash
  Punch names with different action records. Runtime HUD evidence confirms opponent
  `$91`; this does not establish ownership of the player bank.
- The ordinary unlock bitset is exactly 64 bits and progression calls cover every
  ID `$00-$3F`. The six exceptional IDs fall outside that proven progression path.

## Remaining questions

1. Which runtime state selects the first versus second 32-action player bank?
2. How, if at all, are exceptional IDs `$40-$45` equipped or selected?
3. Which working literal labels should receive final approved localization forms?
4. Which opponent IDs are aliases of player identities, and which are opponent-only
   techniques?
