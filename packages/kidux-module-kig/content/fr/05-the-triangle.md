---
source_sha256 = "f53568357ae2debded090a9254c46174519711f9936def10db3b6c4db9b56b79"
---
# Un triangle aux trois côtés égaux

C'est la plus ancienne construction de la géométrie, vieille de deux
mille ans. Avec deux cercles, tu fais un triangle dont les trois côtés
ont exactement la même longueur, et il reste ainsi quand tu le déplaces.

![Deux cercles et le triangle équilatéral](images/kig-triangle.svg)

@mission missions/triangle.kig

1. Ouvre la mission. Les points A et B, et le cercle de centre A qui
   passe par B.
2. ![Cercle par centre et point](images/tools/circlebcp.svg) Appuie sur
   **Cercle par centre et point**, clique sur B, puis sur A : le cercle
   de centre B qui passe par A.
3. ![Intersection](images/tools/curvelineintersection.svg) Appuie sur
   **Intersection**, clique sur un cercle, puis sur l'autre. Kig marque
   les deux croisements. Appelle celui du haut C : clic droit dessus,
   **Nommer...**.
4. ![Segment](images/tools/segment.svg) Appuie sur **Segment** et clique
   sur A, puis sur B. Encore de B à C, et de C à A.
5. Déplace A ou B. Le triangle grandit et rétrécit, mais ses trois côtés
   restent égaux.

> [think] Pourquoi ? AC est un rayon du premier cercle, donc il est aussi
> long que AB. BC est un rayon du second, donc il est aussi long que AB,
> lui aussi. Trois côtés égaux.

::: try
Cache les deux cercles : clic droit sur chacun, **Cacher**. Puis trouve
le milieu de chaque côté et relie les milieux : quatre petits triangles,
tous égaux. Déplace A.
:::
