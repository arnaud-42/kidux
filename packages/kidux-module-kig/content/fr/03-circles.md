---
source_sha256 = "245efd3524d2cf8f92b0e566344768f0e931f9191f0ae3734d16088d003bc0db"
---
# Les cercles

Un cercle, c'est tous les points qui sont à la même distance de son
centre. Dans Kig, tu en traces un avec son centre et un point par lequel
il passe.

![Deux cercles qui se coupent](images/kig-circles.svg)

@mission missions/deux-cercles.kig

1. Ouvre la mission. Il y a un cercle de centre A qui passe par B.
2. ![Cercle par centre et point](images/tools/circlebcp.svg) Appuie sur
   **Cercle par centre et point**, clique sur B, puis sur A. Un deuxième
   cercle, de centre B, qui passe par A.
3. ![Intersection](images/tools/curvelineintersection.svg) Les cercles se
   coupent en deux endroits. Appuie sur **Intersection** et clique sur un
   cercle, puis sur l'autre. Kig marque les deux points où ils se
   coupent.
4. Éloigne B de A. Les cercles grandissent ensemble et les points
   d'intersection bougent avec eux.

> [cheer] Les deux cercles ont toujours la même taille : le rayon de
> chacun est la distance de A à B. Déplacer un point change cette
> distance pour les deux.

## Un point qui vit sur un cercle

1. ![Cercle par centre et point](images/tools/circlebcp.svg) Appuie sur
   **Cercle par centre et point** et clique à deux endroits vides : un
   cercle, avec son centre et un point dessus.
2. ![Point](images/tools/point.svg) Appuie sur **Point** et clique
   exactement sur le trait du cercle.
3. Déplace ce point. Il glisse le long du cercle et ne le quitte jamais.

::: try
Appuie sur **Segment**, clique sur le centre du cercle, puis sur le
point qui vit sur le cercle. Fais tourner le point. Le segment est
toujours un *rayon* : sa longueur ne change jamais.
:::
