---
source_sha256 = "12dfaae42d84cb3bccb91f26615ecc951bc54a7215993cae2c19e9d97f15e551"
---
# Le milieu d'un segment

Un segment a un milieu, et Kig peut le trouver pour toi. Mieux : le
milieu qu'il trouve reste au milieu quand tu bouges les bouts.

![Un segment et son milieu](images/kig-middle.svg)

@mission missions/milieu.kig

1. Ouvre la mission. Tu vois un segment de A à B et son milieu M.
2. Déplace A vers le haut. Déplace B loin vers la droite. Regarde M.

> [think] M est toujours exactement à mi-chemin, quelle que soit la
> façon dont tu bouges A et B. Kig se souvient que M est *le milieu de
> AB*, et pas un point que tu as posé là.

## Fais-le toi-même

1. ![Segment](images/tools/segment.svg) Appuie sur **Segment** et clique
   à deux endroits vides.
2. ![Milieu](images/tools/bisection.svg) Appuie sur **Milieu** et clique
   sur un bout du segment, puis sur l'autre. Le milieu apparaît.
3. ![Point](images/tools/point.svg) Appuie sur **Point** et clique près
   du segment, mais pas dessus. Ce point est libre : déplace les bouts
   du segment, il reste où il est.

::: try
Trouve le milieu de chaque côté d'un triangle, et relie les trois
milieux par des segments. Quelle forme y a-t-il à l'intérieur ? Déplace
un coin du grand triangle.
:::
