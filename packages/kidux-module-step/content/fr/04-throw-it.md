---
source_sha256 = "57d6dfe911944053d96a6aa42ffdc33a31ef49c0bf8a7f779601e9a4053d7e15"
---
# Lance-la

Lance une balle et elle vole en suivant une courbe : elle monte, passe
au-dessus et redescend. Step peut dessiner cette courbe pour toi.

![Une balle et l'arc qu'elle décrit en volant](images/step-throw.svg)

@mission missions/lancer.step

1. Ouvre la mission. Une balle à gauche, avec une vitesse déjà réglée,
   et un **Traceur** dessus qui dessine là où elle passe.
2. Appuie sur **Simuler**. La balle vole en arc et le traceur laisse son
   chemin derrière elle.
3. Arrête et appuie sur **Annuler** jusqu'à ce que la balle soit
   revenue. Clique dessus et mets sa vitesse à (6, 4). Simule. Puis
   (4, 6). Quel lancer va le plus loin ? Lequel monte le plus haut ?

> [think] Le premier nombre est la vitesse sur le côté, le second la
> vitesse vers le haut. Le haut décide jusqu'où elle monte ; le côté,
> avec le temps passé en l'air, décide jusqu'où elle va.

## Fais-le toi-même

1. Un nouveau monde, avec **ForcePesanteur** et une **Particule**.
2. Dans **Propriétés**, mets sa vitesse à (5, 5).
3. **Traceur** dans la palette, puis clique sur la balle.
4. Simule.

::: try
Trouve la vitesse qui fait arriver la balle exactement en x = 10. Puis
essaie d'y arriver avec une vitesse totale plus petite.
:::
