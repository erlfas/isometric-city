# Case: The Drowned Scribe

The case document for the first story. It records the truth, the timeline, what every story character knows and hides, every clue and its routes, the items, the timed events and the endings. Dialogue (`story/*.ink`) is written from this document; when the two disagree, this document wins until it is changed.

Status: **accepted** (2026-11-15). The review decisions are in §10.

---

## 1. The truth

**Victim.** Mikołaj Pisarz, town scribe of Lublin for thirty years, aged 61. His eyes were failing, so a month ago he asked the wójt to appoint a successor and wrote privately to a young scribe he had met in Prague: **Jan of Sandomierz**.

**What Mikołaj found.** While making a fair copy of the town register (*księga miejska*) for the royal tax collector, he found three entries in a hand imitating his own:
1. A sale of the house *Pod Kotłem* on the market square from **Henryk Kesselhut** to his brother-in-law in Wrocław, dated a week *before* the bench court judged the house forfeit to Kesselhut's Kraków creditor. The sale puts the house out of the creditor's reach.
2. & 3. Two years of toll and *szos* (town tax) exemptions for Kesselhut's cloth, "by council grant", for which no council session exists.

Kesselhut is a councillor (*rajca*) and holds the second key to the register chest. He wrote the entries himself on evenings when he took the register "to check the accounts".

**What Mikołaj did.** He cut the three leaves out of the register so they could not be scraped and rewritten. He meant to lay them before the full council at the next session. Two days before he died, he gave them, sewn into a sealed packet, to his confessor **Brother Wincenty** at the Dominican friary. He asked Wincenty to hand the packet only to the wójt in council, or to "the man I have sent for, who will carry my letter".

**The killing.** Mikołaj, a fair man, wanted to give Kesselhut a chance to confess to the council himself. He told him he had the leaves. Kesselhut sent a sealed note asking to meet "to settle the matter between us, on the river, after vespers, where no one listens". At about 22:00 on the night of day −1, on the Bystrzyca footbridge (*Most Bystrzycki*), Kesselhut asked for the leaves. Mikołaj refused, and Kesselhut struck him on the back of the head with his iron-shod walking staff. Mikołaj fell against the rail and into the water. The current carried him into the mill race, and he lodged at the wheel grate.

**After.** Kesselhut came back after curfew. The night watchman at the Kraków Gate, **Sędziwój**, opened the wicket for him for a Hungarian gold florin and didn't look closely at the hooded man. On the night of day 0, Kesselhut slipped into Mikołaj's lodgings through the unbarred yard door (how is open: §10 Q3) and searched the document chest. He didn't find the leaves.

**Discovery.** At matins on day 0, Bartosz the miller found the body at the wheel grate. Before raising the alarm, he took the dead man's purse.

**Public story (what the town believes when Jan arrives).** The old man's eyes were bad, he went walking by the river in the dark, and he fell. Some whisper suicide, which would mean burial outside consecrated ground. The funeral is set for day 2, pending the parish priest's decision.

---

## 2. Timeline

| When | Where | What happens |
|---|---|---|
| ~4 weeks before | Town hall | Mikołaj finds the false entries while copying the register. |
| ~3 weeks before | — | Mikołaj writes to Jan in Prague; the wójt sends Jan a letter of appointment. |
| Day −3 | Town hall | Mikołaj cuts the three leaves out. |
| Day −2, after sext | Dominican friary | Mikołaj makes his confession and leaves the sealed packet with Brother Wincenty. Seen by the housekeeper (he "carried a bundle to the friars and came back without it"). |
| Day −1, afternoon | Market square | Mikołaj tells Kesselhut he holds the leaves. A boy brings Mikołaj a sealed note (Kesselhut's merchant mark in the wax). |
| Day −1, after vespers | Lodgings | Mikołaj tells the housekeeper he is going "to settle a debt on the river". He takes his lantern and his spectacles. |
| Day −1, ~20:30 | Kraków Gate | Mikołaj leaves the town before curfew. Sędziwój remembers him. |
| Day −1, ~22:00 | Footbridge | The killing. Mikołaj's lantern breaks and falls into the reeds by the bridge's south end. His spectacles fall onto the bank below the bridge. |
| Day −1, ~23:00 | Kraków Gate | Kesselhut is let in through the wicket for a Hungarian florin. |
| Day 0, matins | Mill | Bartosz finds the body and takes the purse, which holds the note, a few groschen and Mikołaj's small seal. Then he raises the alarm. |
| Day 0, terce | Fara (parish church) | The body is laid out in a side chapel. |
| Day 0, night | Lodgings | Kesselhut searches the document chest. A thread of dyed Flemish broadcloth catches on the hasp. The housekeeper hears footsteps but is afraid to look. |
| Day 0, vespers | Brewer's, ul. Kozia | Sędziwój spends the florin on drink and a debt. The brewer keeps the coin as a curiosity. |
| **Day 1, matins** | **Kraków Gate** | **Jan arrives. The game begins.** |
| Day 2, terce | Fara, then churchyard | Funeral (see §6 E2). |
| Day 3, terce | Market square | Fair day; Hungarian wine caravan arrives (existing fair event). |
| Day 3, nones | Town hall | Council session; the accusation can be made (§7). It is repeated each day after day 3 at nones. |

---

## 3. Places

Coordinates from `public/city_plan.json`. Which parcels exactly are picked in M5.

| Place | Plan id / position | Role in the story |
|---|---|---|
| Kraków Gate | `gate_krakow` (−160, −80) | Opening scene; the wicket; Sędziwój's post at night. Shuts at compline (21:00). |
| Town hall | `town_hall` (0, 0) | Jan's desk, the register chest, the wójt by day, council session. |
| Jan's lodging | `p_001_player_workshop` (−235, −120), Kraków suburb | Bed, sleep and save. Its current residents and workers move elsewhere. |
| Mikołaj's lodgings | a small tenement near the town hall (picked in M5) | Housekeeper; document chest; wax tablet. |
| Kesselhut's house *Pod Kotłem* | `p_020` (10, 34), Rynek north side, patrician stepped kamienica | Home; merchant mark carved over the door. |
| Szmatruz | `szmatruz` (22, −20) | Kesselhut's cloth stall by day; bales sealed with his mark. |
| Fara | `parish_fara` (130, 20) | The body in the side chapel, days 1–2; funeral. |
| Dominican friary | `dominican_monastery` (−60, −90) | Brother Wincenty; the packet in the friary library. |
| Footbridge | `most_bystrzycki` (96.5, −194.8) | Scene of the killing; lantern in the reeds; spectacles on the bank. |
| Watermill | `p_watermill_bystrzyca` (128.5, −215.2); race starts at the bridge's south end | Bartosz; wheel grate; purse hidden in a grain bin. |
| Brewer's | a brewer near the Kraków Gate, e.g. ul. Kozia `p_071` (−122.8, −6.3) | The guard's tavern; the florin. |
| Goldsmith | Barbara's workshop, `p_280` (−228, 15), Kraków suburb | She identifies the merchant mark. |

The footbridge and mill are **outside the walls**. Getting there and back after compline means passing a gate, and that is what makes the gate watch matter.

---

## 4. Cast

All are existing plan citizens, renamed and given fixed looks in M5. The proposed citizen ids are candidates only.

| # | Character | Kit | Wants | Knows | Hides / lies about | Daily routine (story overrides in *italics*) |
|---|---|---|---|---|---|---|
| 1 | **Wójt Piotr z Bychawy**, the town's chief official (a royal factor's house, `cit_1386`?) | merchant | A quiet town and no scandal before the fair. | That he appointed Jan; that the register has missing leaves (Jan tells him); not the forgery. | Nothing, but he plays down the death: "an old man's fall". | Town hall by day; home at vespers. |
| 2 | **Henryk Kesselhut**, cloth merchant, councillor (`cit_1382`, home `p_020`) | merchant | To keep his house and his name; to find the leaves. | Everything. | That he met Mikołaj; that he went out after curfew; that he searched the lodgings. | Szmatruz by day; council at nones on day 3. *After Jan asks about the register: he visits Jan, friendly and fishing (E3). After Jan learns of the packet: he goes to the friary at vespers (E4).* |
| 3 | **Bartosz**, miller (`cit_0151`) | farmer | Not to hang for robbing a corpse. | Where and how he found the body, including the wound on the back of the head; what was in the purse. | The purse. He says he "touched nothing, God's truth". | Mill from prime to vespers. *After he is questioned about the purse: he goes to the brewer's at vespers instead of home (the mill is empty).* |
| 4 | **Agnieszka**, Mikołaj's housekeeper (a townswoman) | townswoman | To see her master buried in holy ground; her wages. | He left after vespers "to settle a debt on the river"; he took his lantern and spectacles; the packet to the friars; footsteps on the night of day 0. | That she heard the footsteps and didn't look. She's ashamed and says so only when Jan is kind. | Lodgings; market at terce; Fara at vespers to pray by the body. |
| 5 | **Brother Wincenty OP**, confessor (a Dominican friar) | friar | To keep the seal of confession and his promise to Mikołaj. | That Mikołaj feared for his life; he holds the packet. | He cannot speak of the confession; he speaks only in hints ("Some trusts outlive the one who gives them"). | Friary; Fara at terce on day 2 for the funeral. |
| 6 | **Sędziwój**, night watchman at the Kraków Gate (`cit_0224`) | guard | To keep his post. | He saw Mikołaj leave at ~20:30, and let in a hooded man after 23:00 for a gold coin: tall, a fur-lined cloak, an iron-shod staff, "spoke Polish like a German". | The bribe. He claims he "never opened the wicket". | Gate at night (compline to matins); asleep at home by day. |
| 7 | **Dorota**, brewer-tavernkeeper near the gate (`cit_0063`?) | brewer (townswoman kit for a woman) | Her debts paid. | Sędziwój drank late on day 0 and paid with a Hungarian florin, "gold, the man never had gold in his life". | Nothing; she is the honest gossip. | Brewer's all day; busiest at vespers. |
| 8 | **Barbara Rusinowa**, goldsmith, guild master (`cit_0068`, `p_280`) | townswoman | Business; she dislikes Kesselhut's late payments. | She cut Kesselhut's seal ring with his merchant mark (a kettle over a cross) and keeps a lead proof of every seal she makes. | Nothing. | Workshop from prime to vespers. |

Ambient citizens: a few generic lines by trade and time of day, plus two rumour lines that point at story characters ("Ask the miller, he found him", "The friars buried his secrets, they say").

---

## 5. Clues

Each clue has at least two routes (the story lint checks this). **Bold** clues are needed for the full-proof ending (§7).

| Id | Clue | Route A | Route B | Route C |
|---|---|---|---|---|
| C1 | Leaves are cut out of the register | Examine the register at his desk, day 1 (tutorial). | The wójt mentions "Mikołaj's mess, pages missing". | — |
| **C2** | **The leaves concerned Kesselhut's house and exemptions** | The register's own index at the front still lists the cut entries: examine the register with Mikołaj's spectacles (I3), since the index is faded and tiny. | Mikołaj's wax tablet (I6) at his lodgings: "K. — not my hand. Sale before the judgment?" | Reading the packet (I11) gives this too. |
| C3 | He didn't fall by accident: he was struck from behind | Examine the body in the Fara side chapel (days 1–2): wound on the back of the head. | Bartosz describes the wound when pressed. | — |
| C4 | He went into the water at the footbridge, not at the mill | The broken lantern (I4) in the reeds at the bridge's south end. | The spectacles (I3) on the bank below the bridge. | — |
| C5 | He went to meet someone | Agnieszka: "a debt to settle on the river". | The note (I8) from the purse. | — |
| C6 | Bartosz took the purse | Search the mill while it is empty (after E5): the purse (I7) is in a grain bin. | Show Bartosz the spectacles or describe the empty belt; he breaks down and hands it over if Jan promises silence (a moral choice: the promise binds later dialogue with the wójt). | — |
| **C7** | **The note was sealed with Kesselhut's merchant mark** | Show the note (I8) to Barbara; she knows the mark and shows her lead proof (I10). | Compare the wax with the mark over *Pod Kotłem*'s door or on his bales at the Szmatruz (examine with the note in hand). | — |
| C8 | Someone searched the lodgings after his death | Agnieszka (footsteps) once Jan is kind or shows the disturbed chest. | Examine the chest: forced order, and the broadcloth thread (I9) on the hasp. | — |
| C9 | The thread is costly dyed Flemish broadcloth sold by few | Examine the thread at the Szmatruz bales (matches Kesselhut's scarlet). | Barbara or Dorota: "only Kesselhut wears that scarlet". | — |
| **C10** | **A man came back through the gate after curfew and paid in gold** | Dorota tells about the florin and gives or sells it (I12). | Sędziwój confesses when shown the florin, or when Jan threatens to tell the wójt. | — |
| C11 | That man was tall, in a fur-lined cloak, with an iron-shod staff | Sędziwój, after C10. | Kesselhut's staff: examine it during E3 (a dent and a dark stain on the ferrule). | — |
| **C12** | **The leaves exist, and Wincenty holds them** | Agnieszka: "he took a bundle to the friars two days before". | Mikołaj's letter (I2): "I have entrusted what matters to the one who keeps secrets." | Wincenty's hints when asked about Mikołaj's last confession. |
| **C13** | **The leaves themselves (the packet)** | Show Wincenty Mikołaj's letter (I2) after C12: he gives Jan the packet. | Prove murder to him (C3 + C4): his conscience lets him give it to "the man who seeks justice". | — |

**Proof sets** (the council's test):
- **Motive**: C13, or C2 + C1.
- **Link to the meeting**: C7.
- **Opportunity**: C10, or C11.

The full proof is motive plus at least one of link and opportunity. C13 is required for the best ending, because without the leaves Kesselhut can say the index was misread.

---

## 6. Timed events

| Id | When | Trigger / condition | What happens | If missed |
|---|---|---|---|---|
| E1 | Day 1, matins | Game start | Jan reaches the Kraków Gate; Sędziwój questions him (dialogue tutorial) and points the way to the town hall. | — |
| E2 | Day 2, terce | Fixed | Funeral at the Fara. If Jan has shown the priest C3 by then, Mikołaj is buried in the churchyard; otherwise outside it, by the wall. Everyone in the cast attends; Kesselhut speaks kindly of the dead. It's a chance to observe the staff (C11 route B). | Burial outside consecrated ground. Agnieszka is colder, and the kindness route to C8 needs the chest instead. No clue is lost. |
| E3 | The first evening after Jan asks anyone about the register's missing leaves | Story flag | Kesselhut calls on Jan at his lodging at vespers, offers friendship and "help with the old man's papers", and asks whether Jan has found any. Jan can lie, tell the truth or deflect; telling the truth triggers E4 early. | Not missable (it comes to Jan). |
| E4 | The vespers after Kesselhut learns of the friars (Jan tells him in E3, or Jan has had C12 for a full day) | Story flag | Kesselhut goes to the friary to ask Wincenty for "the scribe's things". Wincenty refuses. If Jan is there, he sees it, which strengthens C11. | Nothing lost: Wincenty refuses either way. This is pressure, not a trap. |
| E5 | The vespers after Bartosz is questioned about the purse | Story flag | Bartosz goes to the brewer's; the mill is empty until compline. | Repeats each evening while the flag holds. |
| E6 | Day 3, terce | Fixed (existing fair event) | Fair; the Hungarian caravan arrives. Dorota mentions "gold like Sędziwój's", a nudge towards C10. | Only a hint. |
| E7 | Day 3, nones, then daily at nones | Fixed | Council session at the town hall; Jan may accuse (§7). | Repeats daily. |

---

## 7. The accusation and endings

At a council session (E7), Jan may stand and accuse. The dialogue asks **who** (any of the cast), **how** (struck, pushed, or "he fell"), and **why** (the forged entries, a debt, theft, a quarrel). Then he lays out evidence from his inventory and journal.

| Ending | Condition | Outcome |
|---|---|---|
| **Justice** | Accuses Kesselhut, with full proof (§5) including C13 | The leaves are read aloud; Kesselhut is held for the royal court; the house goes to the creditor; Mikołaj is moved to the churchyard if he lay outside it. Jan is confirmed as town scribe. |
| **The councillor's word** | Accuses Kesselhut without full proof | The council won't condemn one of its own on a scribe's suspicion. Kesselhut is warned; Jan keeps his post but is watched. In a final scene, Kesselhut thanks him "for his discretion". |
| **The wrong man** | Accuses anyone else | The accused is taken (Bartosz is pilloried as a corpse-robber and blamed for the death; Sędziwój loses his post and is flogged). Kesselhut offers Jan his support "for clearing this up so quickly". |

Jan can also refuse to accuse at all, and keep investigating; the session simply passes.

---

## 8. Items

About 18 items, all hand-placed. Use, give and show reactions are written in Ink; this table lists what each item is for.

| Id | Item | Where / how obtained | Used for |
|---|---|---|---|
| I1 | Letter of appointment (the wójt's seal) | Start inventory | Shown to Sędziwój at the gate (tutorial) and to the wójt. |
| I2 | Mikołaj's letter to Jan | Start inventory | Examining it reveals C12 route B; showing it to Wincenty gives C13. |
| I3 | Mikołaj's spectacles (riveted lenses, Italian) | Bank below the footbridge | C4; reading the register index (C2); shown to Bartosz (C6). |
| I4 | Broken lantern | Reeds at the footbridge's south end | C4. |
| I5 | Register keys | Given by the wójt on day 1 | Opens the register chest at the town hall. |
| I6 | Wax tablet and stylus | Mikołaj's lodgings, desk | C2 route B. |
| I7 | Mikołaj's purse | Mill grain bin, or from Bartosz | Contains I8 and Mikołaj's small seal; C6. |
| I8 | Wet sealed note (unreadable) | From the purse | Combine with a candle or hearth (dry it by the fire): readable, "on the river, after vespers…". The wax mark is C7. |
| I9 | Scarlet broadcloth thread | Hasp of the document chest | C8, C9. |
| I10 | Lead seal proof | Barbara, after showing her I8 | C7, as evidence for the council. |
| I11 | The sealed packet (the three leaves) | Wincenty (C13) | C2; motive at the council. |
| I12 | Hungarian gold florin | Dorota, given or bought | C10; shown to Sędziwój. |
| I13 | A few groschen | Start inventory | Buying the florin, bread and ale (small talk). |
| I14 | Candle | Jan's lodging, or the Fara | Combine with I8. |
| I15 | Miller's pole-hook | At the mill | Use it on the wheel grate: it recovers Mikołaj's lodgings key, which opens his lodgings if Agnieszka is out. |
| I16 | Mikołaj's lodgings key | From the grate (I15), or Agnieszka gives Jan hers | A second way into the lodgings. |
| I17 | Bread loaf | Any baker's window | Given to Agnieszka (kindness, the route to C8), or as a small social key. |
| I18 | Rosary (Mikołaj's) | On the body, given by the priest | Given to Agnieszka; softens her completely. A side scene. |

There are no dead ends: I11, I3 and I8 can't be given away or lost, and items given to a character can be got back from them by asking.

---

## 9. Engine requirements this story needs

These feed the plan (`docs/rpg_plan.md`) and are listed by milestone.

- **M1 (Jan in town):** Jan walks outside the walls and through the gates; the gates close at compline, with a wicket that only opens through dialogue.
- **M3 (items):** items placed inside interiors (lodgings, mill, friary library) and outdoors (reeds, bank); inspectable fixed objects (register, chest, door mark, bales, staff, body, wheel grate).
- **M4 (journal):** clues logged with their source; the proof-set check.
- **M5 (story controls):**
  - Story overrides of routines (E3, E4, E5).
  - Visits to Jan's lodging (E3).
  - The body laid out in the Fara, as a prop plus a slot.
  - The funeral gathering (E2).
  - The council session gathering at the town hall (E7).
  - Removing the residents and workers from `p_001_player_workshop`.
- **M6 (the story):** a priest at the Fara as a minor speaking role (burial decision) and the boy messenger, mentioned only.

---

## 10. Review decisions (2026-11-15)

1. **Wincenty and the packet.** The packet was handed to him outside confession, so he may give it up. What was said in confession he never repeats.
2. **The funeral's stakes.** Whether Mikołaj is buried inside or outside the churchyard depends on whether Jan proves C3 by day 2.
3. **How Kesselhut got into the lodgings.** Agnieszka's yard door was unbarred. Mikołaj's key fell from the body and lodged in the wheel grate (I15–I16).
4. **Bartosz's promise.** If Jan breaks his promise to Bartosz, Bartosz won't speak to him again and the wójt notes that Jan broke his word. The ending is unchanged.
5. **Naming.** The wójt is **Piotr z Bychawy**.
6. **Violence.** The killing is never shown. The body is a shrouded figure, and the wound is described in text only.