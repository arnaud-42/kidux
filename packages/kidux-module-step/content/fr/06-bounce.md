---
source_sha256 = "a8566e4999275d45c7a9c46bc889859783ef4e58990057c807853b1b28ad918a"
---
# Rebonds et chocs

Les balles rebondissent sur les murs et se cognent entre elles. Step
sait comment.

![Une balle qui rebondit sur une boîte](images/step-bounce.svg)

@mission missions/rebond.step

1. Ouvre la mission. Un disque au-dessus d'une boîte tenue immobile par
   un point d'ancrage, la pesanteur en marche, et un solveur de
   collisions dans la liste du monde : c'est lui qui fait rebondir les
   objets au lieu de les laisser passer à travers.
2. Appuie sur **Simuler**. Le disque tombe, touche la boîte et
   rebondit.
3. Ajoute un deuxième **Disque** depuis la palette, donne-lui une vitesse
   vers le premier, et simule. Ils se cognent et s'écartent.

> [cheer] Chaque rebond obéit à une règle : ce qu'une balle perd en
> vitesse, l'autre le gagne. Rien n'est perdu, tout est transmis.

## Fais-le toi-même

1. Un nouveau monde. Une **Boîte** depuis la palette, dessinée large et
   plate.
2. **Point d'ancrage** depuis la palette, puis clique sur la boîte : elle
   reste où elle est, quoi qui la tire.
3. Un **Disque** au-dessus. **ForcePesanteur**, et clique sur le plan.
4. Simule. Un nouveau monde a déjà son solveur de collisions.

::: try
Fais une pente : une boîte inclinée en mettant son *angle* à 0.3. Laisse
un disque rouler dessus. Puis essaie **Gaz** depuis la palette : une
centaine de particules qui rebondissent dans une boîte, et c'est ça,
l'air.
:::
