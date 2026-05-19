---
title: "Inside the Competitive System"
date: 2026-05-15
author: "Lutraa"
summary: "A full breakdown of how competitive play works in Solaris. Placement games, ranks, the Top 50 leaderboard, matchmaking, and what you earn by climbing."
tags:
  - competitive
  - gameplay
  - deep-dive
  - ranked
  - minecraft-minigame
  - java-edition
thumbnail: "comp.png"
header_image: "/static/images/blog/comp.png"
---

# Inside the Competitive System

Inside every base game on Solaris, there is a fully built-out competitive system. It is designed to give casual players fair, balanced matches and give competitive players something meaningful to grind for.

Here is how it all works.

## Placement Games

Before you start climbing the ranks, you will play **3 placement games**. The system looks at how well you perform in those games and your win/loss ratio to determine your starting rank. Once you are placed, the real climb begins.

## How Points Work

After placement, every game shifts your progress up or down. The base values are:

| Result | Progress |
|--------|----------|
| Win | +20% |
| Loss | -15% |
| 0 to 2 Kills | +0% |
| 3 to 5 Kills | +1% |
| 6 to 9 Kills | +2% |
| 10+ Kills | +3% |

These values will be tuned throughout development and the early months of Solaris. We are also exploring more stats to make your rank reflect your skill more accurately across different game modes.

## The Ranks

There are seven ranks to climb. The first four each contain three divisions (I through III):

1. Bronze I - III
2. Silver I - III
3. Gold I - III
4. Diamond I - III
5. Celestial
6. Eclipse
7. Singularity

## Top 50

Most competitive games have some version of a top-player leaderboard. Ours is the **Top 50**.

To appear on the Top 50, you need to be at least **Diamond rank** and have played a minimum of **25 games** in that mode. The leaderboard lists the highest-ranked players actively competing.

**What do you earn from Top 50?**

Every player in the Top 50 gets a special icon displayed on their profile next to their rank. It is toggleable in your settings if you would rather keep it private. At the end of the season, Top 50 finishers receive an exclusive title showing where they finished, permanently tied to that season.

## Matchmaking

We want every match to be as fair as possible. Here is how queuing works:

**Metal Ranks (Bronze through Diamond):** The system first tries to match players within 5 divisions of each other. If a full lobby cannot be filled, it expands to all metal ranks. If that still does not fill, it opens to all ranks. If the queue widens, it is not your doing and will not be treated as such.

**Top Ranks (Celestial, Eclipse, Singularity):** The system first tries to match top-rank players together. If that does not work, it expands to Diamond and Gold, then to all ranks. Same rule applies: a wide queue is circumstantial, not a reflection on the player.

---

These systems are built to evolve. As Early Access progresses, we will gather feedback, watch the data, and keep refining things to make the ranked experience feel genuinely competitive and fair from the very first season.

See you on the leaderboard.

*Lutraa*
