---
source_sha256 = "ff08797480cb6287a413b4acb6b19e624cdcb74d0c76b39760f4a0c82d729c31"
---
# Perpendiculaire et parallèle

Deux droites sont *perpendiculaires* quand elles se croisent comme un
signe plus. Deux droites sont *parallèles* quand elles ne se croisent
jamais, comme les rails d'un train. Kig trace les deux pour toi, et
elles gardent leur règle quand tu bouges les choses.

![Une droite, un point, et la perpendiculaire et la parallèle qui passent par lui](images/kig-parallels.svg)

@mission missions/paralleles.kig

1. Ouvre la mission. Il y a une droite et un point P en dehors.
2. ![Perpendiculaire](images/tools/perpendicular.svg) Appuie sur
   **Perpendiculaire**, clique sur la droite, puis sur P. Une droite qui
   passe par P coupe la première à angle droit.
3. ![Parallèle](images/tools/parallel.svg) Appuie sur **Parallèle**,
   clique sur la droite, puis sur P. Une droite qui passe par P et ne
   rencontre jamais la première.
4. Déplace P. Les deux nouvelles droites bougent avec lui et gardent
   leur règle.
5. Déplace maintenant l'un des deux points par lesquels passe la
   première droite. La première droite tourne, et les deux autres
   tournent avec elle.

> [think] La parallèle et la perpendiculaire sont *faites à partir* de la
> première droite. Change la première, et elles changent. C'est à ça
> que sert Kig.

## Un carré qui reste carré

1. ![Segment](images/tools/segment.svg) Appuie sur **Segment** et clique
   à deux endroits vides. Appelle ses bouts A et B : clic droit sur
   chacun, **Nommer...**.
2. ![Perpendiculaire](images/tools/perpendicular.svg) Appuie sur
   **Perpendiculaire**, clique sur le segment, puis sur A. Encore une
   fois : **Perpendiculaire**, le segment, puis B.
3. ![Cercle par centre et point](images/tools/circlebcp.svg) Appuie sur
   **Cercle par centre et point**, clique sur A, puis sur B.
4. ![Intersection](images/tools/curvelineintersection.svg) Appuie sur
   **Intersection**, clique sur le cercle, puis sur la perpendiculaire
   qui passe par A. Kig marque les endroits où ils se coupent, en haut et
   en bas : appelle celui du haut D.
5. ![Parallèle](images/tools/parallel.svg) Appuie sur **Parallèle**,
   clique sur le segment, puis sur D.
6. ![Intersection](images/tools/curvelineintersection.svg) Appuie sur
   **Intersection**, clique sur cette parallèle, puis sur la
   perpendiculaire qui passe par B. Appelle le nouveau point C.
7. ![Segment](images/tools/segment.svg) Relie A, B, C et D par des
   segments, en faisant tout le tour. Déplace A ou B : c'est toujours un
   carré.

> [point] Quand plusieurs objets sont sous la souris, Kig demande *Quel
> objet ?* Choisis celui que tu veux.

::: try
Cache les droites et le cercle dont tu t'es servi : clic droit sur
chacun, **Cacher**. Ne garde que le carré. Il marche toujours.
:::
